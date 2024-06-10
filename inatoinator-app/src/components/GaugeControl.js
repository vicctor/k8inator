import React from 'react';

const GaugeControl = ({ title, value, min, max, step, onChange }) => {
  return (
    <div class='container'>
        <div class="row">
          <div class="col-sm">{title}</div>
          <div class="col-sm">
          <input
            type="number" 
            value={value} 
            onChange={(e) => onChange(title, parseInt(e.target.value))}
          />
          </div>
      </div>
    </div>
  );
};

export default GaugeControl;
