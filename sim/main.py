import os
from dataclasses import dataclass
from typing import List, Dict

import requests
import simpy
import random
from flask import Flask, request, jsonify, app, send_from_directory

@dataclass
class PodStats:
    id: int
    cpu: int
    memory: int

@dataclass
class Sample:
    successes: int
    failures: int
    pods: List[PodStats]

# Klasa reprezentująca pojedynczy pod
class Pod:
    def __init__(self, env, name, cpu_limit, memory_limit, cluster, id):
        self.env = env
        self.name = name
        self.cpu = simpy.Container(env, capacity=cpu_limit, init=cpu_limit)  # Initialize with max capacity
        self.memory = simpy.Container(env, capacity=memory_limit, init=0)  # Initialize with 0 used
        self.memory_limit = memory_limit
        self.cluster = cluster
        self.id = id

    def process_request(self, memory_demand, cpu_demand, network_demand, request_duration, network_latency):
        print(f"{self.env.now}: {self.name} started processing request")  # Debug print

        print(
            f"{self.env.now}: {self.name} processing request with {cpu_demand} CPU, {memory_demand} memory, {network_demand} network.")

        with self.cpu.get(cpu_demand) as cpu_request, \
                self.memory.put(memory_demand) as memory_request, \
                self.cluster.network.get(network_demand) as network_request:
            yield  network_request
            latency = random.gauss(network_latency, network_latency * 0.1)
            yield self.env.timeout(latency)
            yield self.env.timeout(request_duration)

        self.cpu.put(cpu_demand)
        self.memory.get(memory_demand)  # Decrease memory usage



# Klasa reprezentująca klaster szkółkarski
class KubernetesCluster:
    def __init__(self, env, pod_cpu_limit, pod_memory_limit, total_pods, network_limit, scaling_time):
        self.next_pod_id = 0
        self.env = env
        self.pod_cpu_limit = pod_cpu_limit
        self.pod_memory_limit = pod_memory_limit
        self.total_pods = total_pods
        self.network = simpy.Container(env, capacity=network_limit, init=network_limit)
        self.pods = [Pod(env, f"Pod-{self._next_pod_id()}", pod_cpu_limit, pod_memory_limit, self, self._next_pod_id()) for i in range(total_pods)]
        self.scaling_time = scaling_time
        self.scaling_in_progress = False
        self.requests_handled = 0  # Number of handled requests
        self.successful_requests = 0  # Number of successfully handled requests
        self.rejected_requests = 0  # Number of rejected requests
        self.samples = []
    
    def _next_pod_id(self):
        self.next_pod_id = self.next_pod_id + 1
        return self.next_pod_id

    def log_stats(self):

        print(f"{self.env.now}: Total pods: {len(self.pods)}, Requests handled: {self.requests_handled},"
              f" Successful requests: {self.successful_requests}, Rejected requests: {self.rejected_requests}")
        for pod in self.pods:
            print(
                f"  {pod.name} - CPU: {pod.cpu.level}/{pod.cpu.capacity}, Memory: {pod.memory.level}/{pod.memory.capacity}")
        sample = Sample(successes=self.successful_requests,
                        failures=self.rejected_requests,
                        pods=[PodStats(p.id, p.cpu.level, p.memory.level) for p in self.pods])
        self.samples.append(sample)

    def handle_request(self, memory_demand, cpu_demand, network_demand, request_duration, network_latency):
        print(f"{self.env.now}: Handling new request")  # Debug print
        self.requests_handled += 1
        allocated_pod = None

        # Sprawdzanie dostępnych podów
        for pod in self.pods:
            if pod.cpu.level >= cpu_demand:
                allocated_pod = pod
                break

        if allocated_pod:
            print(f"{self.env.now}: Allocated pod: {allocated_pod.name}")  # Debug print
            if not (pod.memory.level + memory_demand > pod.memory_limit * 0.5):
                yield self.env.process(allocated_pod.process_request(memory_demand, cpu_demand, network_demand, request_duration,
                                              network_latency))
                self.successful_requests += 1
            else:
                self.rejected_requests += 1
                print(
                    f"{self.env.now}: Request rejected due to memory limit exceeded. Pod {allocated_pod.name} will be terminated.")
                self.remove_pod(allocated_pod)

        else:
            self.rejected_requests += 1
            if not self.scaling_in_progress:
                print(f"{self.env.now}: No available pods with sufficient CPU, scaling up.")
                self.scaling_in_progress = True
                yield self.env.process(self.add_pod())
            else:
                print(f"{self.env.now}: No available pods and scaling in progress. Request rejected due to CPU limit.")

        self.log_stats()

    def add_pod(self):
        # Symulacja czasu potrzebnego na uruchomienie nowego poda
        print(f"{self.env.now}: Scaling up...")  # Debug print
        yield self.env.timeout(self.scaling_time)
        
        new_pod = Pod(self.env, f"Pod-{self._next_pod_id()}", self.pod_cpu_limit, self.pod_memory_limit, self, self._next_pod_id())
        self.pods.append(new_pod)
        self.scaling_in_progress = False
        print(f"{self.env.now}: New pod {new_pod.name} added after scaling")
        self.log_stats()

    def remove_pod(self, pod):
        print(f"{self.env.now}: Removing pod {pod.name} due to memory limit exceeded")
        self.pods.remove(pod)
        self.log_stats()


# Funkcja symulująca przychodzące żądania
def incoming_requests(env, cluster, memory_demand, cpu_demand, network_demand, request_duration, interval,
                      network_latency):
    print(f"{env.now}: Starting to handle incoming requests")  # Debug print
    while True:
        print(f"{env.now}: New incoming request")  # Debug print
        env.process(
            cluster.handle_request(memory_demand, cpu_demand, network_demand, request_duration, network_latency))
        yield env.timeout(interval)


# Główna funkcja symulacji
def simulate_kubernetes_cluster(runtime, pod_cpu_limit, pod_memory_limit, total_initial_pods, network_limit,
                                memory_demand, cpu_demand, network_demand, request_duration, request_interval,
                                network_latency, scaling_time):
    env = simpy.Environment()
    cluster = KubernetesCluster(env, pod_cpu_limit, pod_memory_limit, total_initial_pods, network_limit, scaling_time)
    env.process(
        incoming_requests(env, cluster, memory_demand, cpu_demand, network_demand, request_duration, request_interval,
                          network_latency))
    env.run(until=runtime)
    return cluster.samples

app = Flask(__name__,  static_folder='../inatoinator-app/build/')

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

@app.route('/app', defaults={'path': ''})
@app.route('/app/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy_requests(path):
    print(f"Forward request {request} using path '{path}'")
    node_server_url = 'http://localhost:3000/'  # URL of the Node.js server hosting the React app
    node_request_url = node_server_url + path
    headers = {'Cache-Control': 'no-cache'}
    response = requests.request(
        method=request.method,
        url=node_request_url,
        headers=headers,
        data=request.data
    )

    return response.content, response.status_code, response.headers.items()


@app.route('/simulate', methods=['POST'])
def simulate_kubernetes():
    parameters = [
        ('runtime', 50),  # czas trwania symulacji
        ('pod_cpu_limit', 500),  # limit CPU per pod
        ('pod_memory_limit', 1000),  # limit pamięci per pod
        ('total_initial_pods', 2),  # początkowa liczba podów
        ('network_limit', 1000),  # limit sieci klastra
        ('memory_demand', 300),  # zapotrzebowanie na pamięć per zapytanie
        ('cpu_demand', 200),  # zapotrzebowanie na CPU per zapytanie
        ('network_demand', 50),  # zapotrzebowanie na sieć per zapytanie
        ('request_duration', 1),  # czas trwania zapytania
        ('request_interval', 1),  # interwał pomiędzy zapytaniami
        ('network_latency', 1),  # średnia latencja sieci w jednostkach symulacyjnych (np. sekundach)
        ('scaling_time', 10)    # czas potrzebny na skalowanie i uruchomienie poda w jednostkach symulacyjnych (np. sekundach)
    ]

    data = request.get_json()

    runtime = data.get('runtime', 50)
    pod_cpu_limit = data.get('pod_cpu_limit', 500)
    pod_memory_limit = data.get('pod_memory_limit', 1000)
    total_initial_pods = data.get('total_initial_pods', 2)
    network_limit = data.get('network_limit', 1000)
    memory_demand = data.get('memory_demand', 300)
    cpu_demand = data.get('cpu_demand', 200)
    network_demand = data.get('network_demand', 50)
    request_duration = data.get('request_duration', 1)
    request_interval = data.get('request_interval', 1)
    network_latency = data.get('network_latency', 1)
    scaling_time = data.get('scaling_time', 10)

    # Uruchomienie symulacji
    samples = simulate_kubernetes_cluster(runtime, pod_cpu_limit, pod_memory_limit, total_initial_pods, network_limit,
                                memory_demand, cpu_demand, network_demand, request_duration, request_interval,
                                network_latency, scaling_time)

    return jsonify(samples)

if __name__ == '__main__':
    app.run(debug=True)