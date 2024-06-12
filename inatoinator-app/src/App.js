import './App.css';
import { useState, useEffect } from "react";
//import { setInterval } from "react";
import { Data } from "./Data";

import LineChart from "./components/LineChart";
import ChartComponent from './components/PieChart';

import Chart from "chart.js/auto";
import { CategoryScale } from "chart.js";

import axios from 'axios';

import GaugeControl from './components/GaugeControl';

Chart.register(CategoryScale);

const simulateKubernetes = async (onData, params={}) => {
  const url = '/simulate';
  
  try {
    const response = await axios.post(url, params);    
    onData(response.data)
  } catch (error) {
    console.error(error);
  }
};

function App() {

  const [requestBody] = useState({
    runtime: 60,
    pod_cpu_limit: 600,
    pod_memory_limit: 1200,
    total_initial_pods: 3,
    network_limit: 1500,
    memory_demand: 400,
    cpu_demand: 250,
    network_demand: 75,
    request_duration: 2,
    request_interval: 2,
    network_latency: 1.5,
    scaling_time: 12
});

  const datasetTemplate = {
    labels: [], 
    datasets: [
      {
        data: [],
        backgroundColor: [
          "rgba(75,192,192,1)",
          "#50AF95",
          "#f3ba2f",
          "#2a71d0"
        ],
        borderColor: "black",
        borderWidth: 0,
        pointBorderWidth: 0.1,
        pointRadius: 0.9,
      }
    ]
  }

  const statsLineTemplate = {
    pointBorderWidth: 0.1,
    pointRadius: 0.9
  }

  const [failuresData, setFailuresData] = useState({...datasetTemplate});
  const [successesData, setSuccessesData] = useState({...datasetTemplate});
  const [errorrateData, setErrorrateData] = useState({...datasetTemplate});
  const [podsCountData, setPodsCountData] = useState({...datasetTemplate});
  const [podsMemData, setPodsMemData] = useState({...datasetTemplate});
  const [podsCpuData, setPodsCpuData] = useState({...datasetTemplate});

  const handleGaugeChange = (parameter, value) => {
    requestBody[parameter] = parseInt(value); 
    simulateKubernetes((data) => {
          // data is an array of ojects hahing fileds, extract to array field "failrues" 
          const y = data.map((d) => d.failures)
          // create indexes array from data
          const x = Array.from({ length: data.length }, (_, i) => i);
          // create chart data array from data
          setFailuresData({...failuresData, labels: x, datasets: [{ ...failuresData.datasets[0], data: y }], });
          setSuccessesData({...successesData, labels: x, datasets: [{ ...successesData.datasets[0], data: data.map((d) => d.successes) }],});
          setErrorrateData({...errorrateData, labels: x, datasets: [{ ...errorrateData.datasets[0], data: data.map((d) => (d.failures / Math.max(1, d.successes)) * 100) } ],});
          setPodsCountData({...podsCountData, labels: x, datasets: [{ ...successesData.datasets[0], data: data.map((d) => d.pods.length) }],});

          var memDatasets = {}
          data.map((d, t) => d.pods.map((pod) => {
            if (memDatasets[pod.id] === undefined) {
              // table of 0 of length t
              var zeros = Array.from({ length: t }, (_, i) => 0)
              memDatasets[pod.id] = {...statsLineTemplate, label: pod.id, data: zeros}
            }
            memDatasets[pod.id].data.push(pod.memory)
          }))
          setPodsMemData({...podsMemData, labels: x, datasets: Object.values(memDatasets),});


          var cpuDatasets = {}
          data.map((d, t) => d.pods.map((pod) => {
            if (cpuDatasets[pod.id] === undefined) {
              var zeros = Array.from({ length: t }, (_, i) => 0)
              cpuDatasets[pod.id] = {...statsLineTemplate, label: pod.id, data: zeros}
            }
            cpuDatasets[pod.id].data.push(pod.cpu)
          }))
          setPodsCpuData({...podsCpuData, labels: x, datasets: Object.values(cpuDatasets),});
      },
      requestBody
    );   
  };

  useEffect(() => {
    simulateKubernetes((data) => {
          // data is an array of ojects hahing fileds, extract to array field "failrues" 
          const y = data.map((d) => d.failures)
          // create indexes array from data
          const x = Array.from({ length: data.length }, (_, i) => i);
          // create chart data array from data
          

      },
      requestBody
    );
  }, []);
  

  return (

    <div className="App">
      <header className="App-header">K8S simulate</header>
      
      <div class="container">
        <div class="row">
        {Object.keys(requestBody).map((key, index) => (
          <div class={"col-sm"}>
            <GaugeControl 
            title={key} 
            value={requestBody[key]} 
            min={0}
            max={100}
            step={1}
            onChange={handleGaugeChange} 
            />
          </div>
        ))}
        </div>
      </div>
      <div class="container charts">
      <LineChart diagramLabel="failures sum" chartData={failuresData} />          
      <LineChart diagramLabel="successes sum" chartData={successesData} />          
      <LineChart diagramLabel="error rate" chartData={errorrateData} />          
      <LineChart diagramLabel="cluster size" chartData={podsCountData} />          
      <LineChart diagramLabel="pods mem" chartData={podsMemData} />          
      <LineChart diagramLabel="pods cpu" chartData={podsCpuData} />          
      </div>
      
    </div>
  );
}

export default App;
