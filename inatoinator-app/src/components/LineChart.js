import React from "react";
import { Line } from "react-chartjs-2";

function LineChart({ diagramLabel, chartData }) {
  return (
    <div class="chart-container">
      <h3 style={{ textAlign: "center" }}>{diagramLabel}</h3>
      <Line
        data={chartData}
        options={{
          plugins: {
            title: {
              display: false
            },
            legend: {
              display: false
            },
            pointBorderWidth: 0
          }
        }}
      />
    </div>
  );
}
export default LineChart;