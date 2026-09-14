import { useEffect, useRef } from "react";
import Plotly from "plotly.js-cartesian-dist-min";

function ChartPreview({ figure, title = "Chart preview" }) {
  const chartElementRef = useRef(null);

  useEffect(() => {
    if (!chartElementRef.current || !figure) return undefined;
    const chartElement = chartElementRef.current;

    const layout = {
      ...figure.layout,
      autosize: true,
      paper_bgcolor: "#ffffff",
      plot_bgcolor: "#ffffff",
      font: {
        ...figure.layout?.font,
        color: "#222222",
        family: "Inter, ui-sans-serif, system-ui, sans-serif",
      },
      margin: {
        l: 55,
        r: 24,
        t: 55,
        b: 55,
        ...figure.layout?.margin,
      },
    };

    Plotly.react(chartElement, figure.data || [], layout, {
      responsive: true,
      displaylogo: false,
      scrollZoom: false,
    });

    return () => Plotly.purge(chartElement);
  }, [figure]);

  return (
    <div
      ref={chartElementRef}
      className="chart-preview"
      role="img"
      aria-label={title}
    />
  );
}

export default ChartPreview;
