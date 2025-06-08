document.addEventListener('DOMContentLoaded', () => {
  const nodes = JSON.parse(document.getElementById('nodes-data').textContent);
  const links = JSON.parse(document.getElementById('links-data').textContent);
  const container = document.getElementById('graph');
  const width = container.clientWidth || 800;
  const height = container.clientHeight || 600;
  const radius = 40;

  const svg = d3
    .select(container)
    .append('svg')
    .attr('width', width)
    .attr('height', height);

  const g = svg.append('g');

  svg
    .append('defs')
    .append('marker')
    .attr('id', 'arrow')
    .attr('viewBox', '0 -5 10 10')
    .attr('refX', 15)
    .attr('refY', 0)
    .attr('markerWidth', 6)
    .attr('markerHeight', 6)
    .attr('orient', 'auto')
    .append('path')
    .attr('d', 'M0,-5L10,0L0,5')
    .attr('fill', '#999');

  const simulation = d3
    .forceSimulation(nodes)
    .force('link', d3.forceLink(links).id((d) => d.id).distance(150))
    .force('charge', d3.forceManyBody().strength(-400))
    .force('center', d3.forceCenter(width / 2, height / 2));

  const link = g
    .append('g')
    .attr('stroke', '#999')
    .attr('stroke-opacity', 0.6)
    .selectAll('line')
    .data(links)
    .join('line')
    .attr('stroke-width', 1.5)
    .attr('marker-end', 'url(#arrow)');

  const node = g
    .append('g')
    .selectAll('g')
    .data(nodes)
    .join('g')
    .call(
      d3
        .drag()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended)
    );

  node
    .append('circle')
    .attr('r', 40)
    .attr('fill', '#69b3a2');

  node
    .append('text')
    .attr('text-anchor', 'middle')
    .attr('dy', 4)
    .text((d) => d.id);

  simulation.on('tick', () => {
    nodes.forEach((d) => {
      d.x = Math.max(radius, Math.min(width - radius, d.x));
      d.y = Math.max(radius, Math.min(height - radius, d.y));
    });

    link
      .attr('x1', (d) => d.source.x)
      .attr('y1', (d) => d.source.y)
      .attr('x2', (d) => d.target.x)
      .attr('y2', (d) => d.target.y);

    node.attr('transform', (d) => `translate(${d.x},${d.y})`);
  });

  svg.call(
    d3.zoom().scaleExtent([0.5, 5]).on('zoom', (event) => {
      g.attr('transform', event.transform);
    })
  );

  function dragstarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
  }

  function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
  }

  function dragended(event, d) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
  }
});
