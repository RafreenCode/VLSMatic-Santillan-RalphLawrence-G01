(() => {
  const workbench = document.querySelector('.workbench');
  if (!workbench) return;

  const prefix = Number(workbench.dataset.prefix);
  const total = 2 ** (32 - prefix);
  const requirements = [...document.querySelectorAll('.requirement-item')];
  const blocks = [...document.querySelectorAll('.subnet-block:not(.subnet-block--available)')];
  const totalNode = document.querySelector('[data-total-capacity]');
  const plannedNode = document.querySelector('[data-planned-capacity]');
  const remainingNode = document.querySelector('[data-remaining-capacity]');
  const fitMessage = document.querySelector('[data-fit-message]');
  const detail = document.querySelector('[data-canvas-detail]');
  const availableBlock = document.querySelector('[data-available-block]');
  const availableCapacity = document.querySelector('[data-available-capacity]');

  const allocationSize = (hosts, stored) => {
    if (stored && Number(stored) > 0) return Number(stored);
    const needed = Math.max(4, Number(hosts) + 2);
    return 2 ** Math.ceil(Math.log2(needed));
  };
  const allocationPrefix = capacity => 32 - Math.log2(capacity);
  const format = value => Number(value).toLocaleString();

  const items = requirements.map((row, index) => {
    const hosts = Number(row.dataset.hosts);
    const capacity = allocationSize(hosts, row.dataset.capacity);
    const item = { hosts, capacity, prefix: allocationPrefix(capacity), row, block: blocks[index] };
    row.querySelector('[data-prefix-preview]').textContent = `/${item.prefix} subnet`;
    row.querySelector('[data-capacity-preview]').textContent = `${format(capacity - 2)} usable hosts`;
    if (item.block) {
      item.block.style.setProperty('--block-span', String(Math.max(2, Math.min(12, Math.ceil((capacity / total) * 12)))));
      item.block.querySelector('[data-block-prefix]').textContent = `/${item.prefix} · ${format(capacity - 2)} usable`;
    }
    return item;
  });
  const planned = items.reduce((sum, item) => sum + item.capacity, 0);
  const remaining = total - planned;
  totalNode.textContent = format(total);
  plannedNode.textContent = format(planned);
  remainingNode.textContent = remaining >= 0 ? format(remaining) : `-${format(Math.abs(remaining))}`;
  remainingNode.parentElement.classList.toggle('is-overflow', remaining < 0);

  if (fitMessage) {
    fitMessage.textContent = remaining >= 0
      ? `${format(remaining)} addresses remain available before allocation.`
      : `This draft exceeds the boundary by ${format(Math.abs(remaining))} addresses.`;
  }
  if (availableBlock) {
    availableBlock.hidden = remaining <= 0;
    if (remaining > 0) {
      availableBlock.style.setProperty('--block-span', String(Math.max(2, Math.min(12, Math.ceil((remaining / total) * 12)))));
      availableCapacity.textContent = `${format(remaining)} addresses`;
    }
  }
  blocks.forEach((block, index) => block.addEventListener('click', () => {
    blocks.forEach(candidate => candidate.classList.remove('is-selected'));
    block.classList.add('is-selected');
    const item = items[index];
    if (detail) detail.textContent = `${item.row.querySelector('.requirement-item__main strong').textContent}: ${format(item.hosts)} hosts need a /${item.prefix} subnet, providing ${format(item.capacity - 2)} usable addresses.`;
  }));
})();
