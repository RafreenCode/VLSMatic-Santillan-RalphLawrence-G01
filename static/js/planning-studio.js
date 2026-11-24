(() => {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const numberFormat = new Intl.NumberFormat();

  const animateCounts = () => {
    if (reducedMotion) return;
    document.querySelectorAll('[data-count]').forEach(node => {
      const target = Number(node.dataset.count);
      if (!Number.isFinite(target) || target <= 0) return;
      const started = performance.now();
      const duration = 520;
      const tick = now => {
        const progress = Math.min(1, (now - started) / duration);
        const eased = 1 - Math.pow(1 - progress, 4);
        node.textContent = numberFormat.format(Math.round(target * eased));
        if (progress < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });
  };

  const setupMessages = () => {
    document.querySelectorAll('.message').forEach(message => {
      message.setAttribute('role', 'status');
      message.addEventListener('click', () => message.remove());
      if (!reducedMotion) {
        message.animate(
          [
            { opacity: 0, transform: 'translateY(-12px)', filter: 'blur(5px)' },
            { opacity: 1, transform: 'translateY(0)', filter: 'blur(0)' },
          ],
          { duration: 360, easing: 'cubic-bezier(.16,1,.3,1)' },
        );
      }
    });
  };

  const setupBoundaryPreview = () => {
    const editor = document.querySelector('[data-boundary-editor]');
    if (!editor) return;
    const address = editor.querySelector('#id_base_network');
    const prefix = editor.querySelector('#id_prefix_length');
    const cidr = editor.querySelector('[data-boundary-cidr]');
    const total = editor.querySelector('[data-boundary-total]');
    const track = editor.querySelector('[data-boundary-track]');
    const update = () => {
      const prefixValue = Number(prefix?.value);
      const validPrefix = Number.isInteger(prefixValue) && prefixValue >= 0 && prefixValue <= 30;
      cidr.textContent = `${address?.value || '0.0.0.0'}/${validPrefix ? prefixValue : '—'}`;
      total.textContent = validPrefix ? numberFormat.format(2 ** (32 - prefixValue)) : '—';
      track.style.setProperty('--boundary-fill', `${validPrefix ? Math.max(4, (32 - prefixValue) / 32 * 100) : 0}%`);
    };
    address?.addEventListener('input', update);
    prefix?.addEventListener('input', update);
    update();
  };

  const setupPlanningStudio = () => {
    const studio = document.querySelector('[data-planning-studio]');
    const dataNode = document.querySelector('#allocation-visualization-data');
    const svg = studio?.querySelector('[data-address-map]');
    const layer = studio?.querySelector('[data-address-segments]');
    if (!studio || !dataNode || !svg || !layer) return;

    let allocations = [];
    try { allocations = JSON.parse(dataNode.textContent); } catch { return; }
    if (!allocations.length) return;
    const byId = new Map(allocations.map(item => [String(item.id), item]));
    const namespace = 'http://www.w3.org/2000/svg';

    const makeRect = (className, x, width) => {
      const rect = document.createElementNS(namespace, 'rect');
      rect.setAttribute('class', className);
      rect.setAttribute('x', x);
      rect.setAttribute('y', '44');
      rect.setAttribute('width', width);
      rect.setAttribute('height', '62');
      rect.setAttribute('rx', '8');
      return rect;
    };

    allocations.forEach((item, index) => {
      const x = item.relative_offset * 1000;
      const width = Math.max(.8, item.relative_span * 1000);
      const group = document.createElementNS(namespace, 'g');
      group.setAttribute('class', `address-segment address-segment--${index % 4}`);
      group.setAttribute('data-requirement-id', item.id);
      group.setAttribute('role', 'button');
      group.setAttribute('tabindex', '0');
      group.setAttribute('aria-label', `${item.name}, ${item.network}/${item.prefix}, ${item.allocated_addresses} addresses`);
      const title = document.createElementNS(namespace, 'title');
      title.textContent = `${item.name}: ${item.network}/${item.prefix}`;
      group.append(title, makeRect('address-segment__shape', x, width));
      const hitWidth = Math.max(22, width);
      group.append(makeRect('address-segment__hit', Math.max(0, Math.min(1000 - hitWidth, x - (hitWidth - width) / 2)), hitWidth));
      layer.append(group);
      const select = () => selectRequirement(String(item.id));
      group.addEventListener('click', select);
      group.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); select(); }
      });
      if (!reducedMotion) {
        group.querySelector('.address-segment__shape').animate(
          [{ transform: 'scaleX(0)', opacity: .45 }, { transform: 'scaleX(1)', opacity: 1 }],
          { duration: 540, delay: Math.min(index * 55, 260), easing: 'cubic-bezier(.16,1,.3,1)', fill: 'both' },
        );
      }
    });

    const end = Math.max(...allocations.map(item => (item.relative_offset + item.relative_span) * 1000));
    if (end < 1000) layer.append(makeRect('address-segment__remaining', end, 1000 - end));

    function selectRequirement(id) {
      const item = byId.get(id);
      if (!item) return;
      studio.querySelectorAll('[data-requirement-id]').forEach(node => node.classList.toggle('is-selected', String(node.dataset.requirementId) === id));
      studio.querySelectorAll('[data-select-requirement]').forEach(node => node.setAttribute('aria-pressed', String(node.dataset.selectRequirement) === id ? 'true' : 'false'));
      const values = {
        '[data-inspector-name]': item.name,
        '[data-inspector-prefix]': `/${item.prefix}`,
        '[data-inspector-network]': item.network,
        '[data-inspector-first]': item.first_usable,
        '[data-inspector-last]': item.last_usable,
        '[data-inspector-broadcast]': item.broadcast,
        '[data-inspector-required]': numberFormat.format(item.required_hosts),
        '[data-inspector-capacity]': numberFormat.format(item.usable_capacity),
        '[data-inspector-explanation]': `${item.name} uses a /${item.prefix} block with ${item.efficiency.toFixed(1)}% host efficiency. Network and broadcast addresses remain reserved.`,
      };
      Object.entries(values).forEach(([selector, value]) => {
        const node = studio.querySelector(selector);
        if (node) node.textContent = value;
      });
      const inspector = studio.querySelector('[data-subnet-inspector]');
      if (inspector && !reducedMotion) inspector.animate([{ boxShadow: '0 0 0 3px rgb(0 160 176 / 35%)' }, { boxShadow: '0 0 0 0 transparent' }], { duration: 420, easing: 'ease-out' });
    }

    studio.querySelectorAll('[data-select-requirement]').forEach(control => control.addEventListener('click', () => selectRequirement(control.dataset.selectRequirement)));
    selectRequirement(String(allocations[0].id));
  };

  const setupDashboardMotion = () => {
    const dashboard = document.querySelector('[data-dashboard]');
    if (!dashboard || reducedMotion) return;
    const heroCopy = dashboard.querySelector('.launch-header__copy');
    const plan = dashboard.querySelector('.hero-plan, .hero-workflow');
    heroCopy?.animate(
      [{ opacity: .25, clipPath: 'inset(0 100% 0 0)' }, { opacity: 1, clipPath: 'inset(0 0 0 0)' }],
      { duration: 680, easing: 'cubic-bezier(.16,1,.3,1)', fill: 'both' },
    );
    plan?.animate(
      [{ opacity: .35, transform: 'translateX(22px)', filter: 'blur(5px)' }, { opacity: 1, transform: 'translateX(0)', filter: 'blur(0)' }],
      { duration: 560, delay: 130, easing: 'cubic-bezier(.16,1,.3,1)', fill: 'both' },
    );
    dashboard.querySelectorAll('.hero-plan__segment').forEach((segment, index) => segment.animate(
      [{ transform: 'scaleX(0)', opacity: .4 }, { transform: 'scaleX(1)', opacity: 1 }],
      { duration: 520, delay: 300 + Math.min(index * 55, 260), easing: 'cubic-bezier(.16,1,.3,1)', fill: 'both' },
    ));
  };

  const setupPageMotion = () => {
    if (reducedMotion) return;
    document.querySelectorAll('.studio-shell:not([data-dashboard]) > header, .studio-shell:not([data-dashboard]) > section, .studio-shell:not([data-dashboard]) > .studio-grid, .studio-shell:not([data-dashboard]) > .boundary-layout').forEach((region, index) => region.animate(
      [{ opacity: .6, transform: 'translateY(16px)' }, { opacity: 1, transform: 'translateY(0)' }],
      { duration: 430, delay: Math.min(index * 65, 220), easing: 'cubic-bezier(.16,1,.3,1)', fill: 'both' },
    ));
    document.querySelectorAll('.auth-context > .wordmark, .auth-context__copy, .auth-form-wrap').forEach((region, index) => region.animate(
      [{ opacity: .45, clipPath: 'inset(0 100% 0 0)' }, { opacity: 1, clipPath: 'inset(0 0 0 0)' }],
      { duration: 520, delay: index * 90, easing: 'cubic-bezier(.16,1,.3,1)', fill: 'both' },
    ));
    document.querySelectorAll('[data-motion-list]').forEach(list => {
      [...list.children].forEach((item, index) => item.animate(
        [{ opacity: .35, transform: 'translateY(14px)' }, { opacity: 1, transform: 'translateY(0)' }],
        { duration: 420, delay: Math.min(170 + index * 55, 380), easing: 'cubic-bezier(.16,1,.3,1)', fill: 'both' },
      ));
    });
    document.querySelectorAll('[data-motion-region]:not(.launch-header)').forEach((region, index) => region.animate(
      [{ opacity: .55, transform: 'translateY(18px)' }, { opacity: 1, transform: 'translateY(0)' }],
      { duration: 460, delay: 220 + index * 70, easing: 'cubic-bezier(.16,1,.3,1)', fill: 'both' },
    ));
    document.querySelectorAll('.form-alert, .field__errors').forEach(alert => alert.animate(
      [{ opacity: .4, transform: 'translateX(-6px)' }, { opacity: 1, transform: 'translateX(0)' }],
      { duration: 260, easing: 'cubic-bezier(.16,1,.3,1)' },
    ));
  };

  setupMessages();
  setupBoundaryPreview();
  setupPlanningStudio();
  setupDashboardMotion();
  setupPageMotion();
  animateCounts();
})();
