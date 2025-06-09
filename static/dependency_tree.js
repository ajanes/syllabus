document.addEventListener('DOMContentLoaded', () => {
  const data = JSON.parse(document.getElementById('tree-data').textContent);
  const container = document.getElementById('tree');
  const width = container.clientWidth || 1100;
  const dx = 10;
  const dy = 200;

  const root = d3.hierarchy(data);
  const treeLayout = d3.tree().nodeSize([dx, dy]);
  treeLayout(root);

  const svg = d3
    .select(container)
    .append('svg')
    .attr('width', width)
    .attr('height', root.height * dx + 100)
    .attr('viewBox', [0, 0, width, root.height * dx + 100].join(' '));

  const g = svg.append('g').attr('font-family', 'sans-serif').attr('font-size', 10);

  g.append('g')
    .selectAll('path')
    .data(root.links())
    .join('path')
    .attr('fill', 'none')
    .attr('stroke', '#555')
    .attr('stroke-width', 1.5)
    .attr('d', d3.linkHorizontal()
      .x(d => d.y)
      .y(d => d.x)
    );

  const node = g.append('g')
    .selectAll('g')
    .data(root.descendants())
    .join('g')
    .attr('transform', d => `translate(${d.y},${d.x})`);

  node.append('circle')
    .attr('r', 4)
    .attr('fill', d => d.children ? '#555' : '#999');

  node.append('text')
    .attr('dy', '0.31em')
    .attr('x', d => d.children ? -6 : 6)
    .attr('text-anchor', d => d.children ? 'end' : 'start')
    .text(d => d.data.name)
    .clone(true)
    .lower()
    .attr('stroke', 'white');
});
