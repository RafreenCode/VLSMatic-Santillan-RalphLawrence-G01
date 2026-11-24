(() => {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const numberFormat = new Intl.NumberFormat();

  const setupMessages = () => {
    const stack = document.querySelector('.message-stack');
    if (!stack) return;
    stack.querySelectorAll('.message').forEach(message => {
      const dismiss = document.createElement('button');
      dismiss.type = 'button';
      dismiss.className = 'message__dismiss';
      dismiss.setAttribute('aria-label', 'Dismiss message');
      dismiss.textContent = 'Dismiss';
      dismiss.addEventListener('click', () => {
        message.remove();
        if (!stack.querySelector('.message')) stack.remove();
      });
      message.append(dismiss);
      if (!reducedMotion) {
        message.animate(
          [
            { opacity: 0, transform: 'translateY(-8px)' },
            { opacity: 1, transform: 'translateY(0)' },
          ],
          { duration: 240, easing: 'cubic-bezier(.16,1,.3,1)' },
        );
      }
    });
  };

  const setupFormFeedback = () => {
    document.querySelectorAll('form[method="post"], form[method="POST"]').forEach(form => {
      form.addEventListener('submit', event => {
        const submitter = event.submitter || form.querySelector('button[type="submit"], input[type="submit"]');
        if (!submitter || submitter.dataset.submitting === 'true') return;
        submitter.dataset.submitting = 'true';
        submitter.setAttribute('aria-busy', 'true');
      });
    });
  };

  const setupCopyButtons = () => {
    const copyText = async value => {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(value);
        return;
      }
      const helper = document.createElement('textarea');
      helper.value = value;
      helper.setAttribute('readonly', '');
      helper.style.position = 'fixed';
      helper.style.opacity = '0';
      document.body.append(helper);
      helper.select();
      document.execCommand('copy');
      helper.remove();
    };

    document.addEventListener('click', async event => {
      const button = event.target.closest('[data-copy-value]');
      if (!button) return;
      const value = button.dataset.copyValue;
      if (!value) return;
      try {
        await copyText(value);
      } catch {
        return;
      }
      const announcer = document.querySelector('[data-copy-announcer]');
      const labelNode = button.querySelector('[data-copy-label]');
      const originalLabel = button.dataset.originalLabel || (labelNode ? labelNode.textContent : '');
      if (!button.dataset.originalLabel && originalLabel) {
        button.dataset.originalLabel = originalLabel;
      }
      button.classList.remove('is-copied');
      void button.offsetWidth;
      button.classList.add('is-copied');
      if (labelNode) labelNode.textContent = 'Copied';
      if (announcer) announcer.textContent = `Copied ${value}`;
      window.clearTimeout(Number(button.dataset.copyTimer || 0));
      const timerId = window.setTimeout(() => {
        button.classList.remove('is-copied');
        if (labelNode && button.dataset.originalLabel) {
          labelNode.textContent = button.dataset.originalLabel;
        }
      }, 1600);
      button.dataset.copyTimer = String(timerId);
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

  const showFloatingTooltip = (tooltip, container, centerRatio, yOffset, titleText, cidrText, detailText) => {
    if (!tooltip || !container) return;
    tooltip.replaceChildren();
    const titleEl = document.createElement('strong');
    titleEl.textContent = titleText;
    const codeEl = document.createElement('code');
    codeEl.textContent = cidrText;
    const spanEl = document.createElement('span');
    spanEl.textContent = detailText;
    tooltip.append(titleEl, codeEl, spanEl);
    tooltip.hidden = false;
    const containerWidth = container.clientWidth || 1;
    const tipWidth = tooltip.offsetWidth || 180;
    const rawLeft = centerRatio * containerWidth - tipWidth / 2;
    const clampedLeft = Math.max(4, Math.min(containerWidth - tipWidth - 4, rawLeft));
    tooltip.style.transform = `translate3d(${Math.round(clampedLeft)}px, ${yOffset}px, 0)`;
    tooltip.classList.add('is-visible');
  };

  const hideFloatingTooltip = tooltip => {
    if (!tooltip) return;
    tooltip.classList.remove('is-visible');
    tooltip.hidden = true;
  };

  const setupDashboardWorkflow = () => {
    const workflow = document.querySelector('[data-hero-workflow]');
    if (!workflow) return;
    const steps = [
      {
        code: 'Base boundary · strict CIDR alignment (/0 – /30)',
        desc: 'VLSMatic verifies your network boundary first so host addresses can never create misaligned subnets.',
      },
      {
        code: 'Largest-first VLSM · usable hosts + network & broadcast',
        desc: 'Requirements are automatically sorted largest-first and packed into the smallest fitting power-of-two blocks.',
      },
      {
        code: 'Persisted plan · exact network, mask, usable range & broadcast',
        desc: 'Every allocation boundary is saved atomically and synchronized across the visual map, inspector, and ledger.',
      },
    ];
    const codeNode = workflow.querySelector('[data-workflow-code]');
    const descNode = workflow.querySelector('[data-workflow-desc]');
    const stageNode = workflow.querySelector('[data-workflow-stage]');
    const triggers = [...workflow.querySelectorAll('[data-workflow-trigger]')];
    triggers.forEach(trigger => {
      trigger.addEventListener('click', () => {
        const idx = Number(trigger.dataset.workflowTrigger);
        const step = steps[idx];
        if (!step) return;
        triggers.forEach((btn, i) => {
          btn.setAttribute('aria-pressed', i === idx ? 'true' : 'false');
          btn.closest('[data-workflow-step]')?.classList.toggle('is-active', i === idx);
        });
        if (codeNode) codeNode.textContent = step.code;
        if (descNode) descNode.textContent = step.desc;
        if (stageNode && !reducedMotion) {
          stageNode.animate(
            [{ opacity: 0.45, transform: 'translateY(4px)' }, { opacity: 1, transform: 'translateY(0)' }],
            { duration: 200, easing: 'cubic-bezier(.16,1,.3,1)' },
          );
        }
      });
    });
  };

  const setupDashboardStudio = () => {
    const dashboard = document.querySelector('[data-dashboard]');
    const heroPlan = dashboard?.querySelector('[data-plan-preview]');
    const dataNode = document.querySelector('#dashboard-plans-data');
    if (!dashboard || !heroPlan || !dataNode) return;

    let plans = [];
    try { plans = JSON.parse(dataNode.textContent); } catch { return; }
    if (!plans.length) return;
    const plansById = new Map(plans.map(plan => [String(plan.id), plan]));

    const stage = heroPlan.querySelector('[data-dashboard-stage]');
    const segBar = heroPlan.querySelector('[data-dashboard-segbar]');
    const emptyNote = heroPlan.querySelector('[data-dashboard-empty]');
    const tooltip = heroPlan.querySelector('[data-dashboard-tooltip]');
    const chipsWrap = heroPlan.querySelector('[data-dashboard-chips]');
    const readout = heroPlan.querySelector('[data-dashboard-readout]');

    let activePlan = plansById.get(String(heroPlan.dataset.activeProjectId)) || plans[0];

    const ensureReadoutMarkup = () => {
      if (!readout || readout.querySelector('[data-readout-name]')) return;
      readout.innerHTML = `
        <div class="hero-subnet-readout__top">
          <div class="hero-subnet-readout__identity">
            <span class="hero-subnet-readout__label">Selected subnet · <b data-readout-hosts></b></span>
            <strong data-readout-name></strong>
          </div>
          <div class="hero-subnet-readout__actions">
            <button type="button" class="copy-btn copy-btn--dark" data-copy-value="" data-readout-copy aria-label="Copy selected subnet CIDR">
              <svg class="icon icon--copy" viewBox="0 0 24 24" aria-hidden="true"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
              <svg class="icon icon--check" viewBox="0 0 24 24" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>
              <code data-readout-cidr></code>
            </button>
            <a class="hero-inspect-pill" data-readout-link href="#"><span>Inspect</span><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14m-6-6 6 6-6 6"/></svg></a>
          </div>
        </div>
        <div class="hero-subnet-readout__ips">
          <div class="hero-ip-cell"><span>First usable</span><code data-readout-first></code></div>
          <div class="hero-ip-cell"><span>Last usable</span><code data-readout-last></code></div>
          <div class="hero-ip-cell"><span>Broadcast</span><code data-readout-broadcast></code></div>
        </div>
      `;
    };

    const selectHeroSubnet = (plan, subnetId, animate = false) => {
      const alloc = plan.allocations.find(item => String(item.id) === String(subnetId));
      if (!alloc || !readout) return;
      ensureReadoutMarkup();
      readout.hidden = false;

      heroPlan.querySelectorAll('[data-hero-segment-id]').forEach(node => {
        const selected = node.dataset.heroSegmentId === String(alloc.id);
        node.classList.toggle('is-selected', selected);
        node.setAttribute('aria-pressed', selected ? 'true' : 'false');
      });
      heroPlan.querySelectorAll('[data-select-hero-subnet]').forEach(btn => {
        const selected = btn.dataset.selectHeroSubnet === String(alloc.id);
        btn.classList.toggle('is-selected', selected);
        btn.setAttribute('aria-pressed', selected ? 'true' : 'false');
      });

      const cidr = `${alloc.network}/${alloc.prefix}`;
      const nameNode = readout.querySelector('[data-readout-name]');
      const cidrNode = readout.querySelector('[data-readout-cidr]');
      const copyBtn = readout.querySelector('[data-readout-copy]');
      const inspectLink = readout.querySelector('[data-readout-link]');
      const firstNode = readout.querySelector('[data-readout-first]');
      const lastNode = readout.querySelector('[data-readout-last]');
      const broadcastNode = readout.querySelector('[data-readout-broadcast]');
      const hostsNode = readout.querySelector('[data-readout-hosts]');

      if (nameNode) nameNode.textContent = alloc.name;
      if (cidrNode) cidrNode.textContent = cidr;
      if (copyBtn) copyBtn.dataset.copyValue = cidr;
      if (inspectLink) inspectLink.href = `${plan.detail_url}?subnet=${alloc.id}`;
      if (firstNode) firstNode.textContent = alloc.first_usable;
      if (lastNode) lastNode.textContent = alloc.last_usable;
      if (broadcastNode) broadcastNode.textContent = alloc.broadcast;
      if (hostsNode) hostsNode.textContent = `${numberFormat.format(alloc.required_hosts)} / ${numberFormat.format(alloc.usable_capacity)} hosts`;

      if (animate && !reducedMotion) {
        readout.animate(
          [{ opacity: 0.55, transform: 'translateY(3px)' }, { opacity: 1, transform: 'translateY(0)' }],
          { duration: 190, easing: 'cubic-bezier(.16,1,.3,1)' },
        );
      }
    };

    const renderHeroPlan = (plan, animateSwitch = false) => {
      activePlan = plan;
      heroPlan.dataset.activeProjectId = String(plan.id);
      hideFloatingTooltip(tooltip);

      const titleNode = heroPlan.querySelector('[data-hero-title]');
      const cidrNode = heroPlan.querySelector('[data-hero-cidr]');
      const cidrBtn = heroPlan.querySelector('[data-hero-cidr-btn]');
      const usageNode = heroPlan.querySelector('[data-hero-usage]');
      const allocNode = heroPlan.querySelector('[data-hero-allocated]');
      const remNode = heroPlan.querySelector('[data-hero-remaining]');
      const subNode = heroPlan.querySelector('[data-hero-subnets]');
      const openLink = heroPlan.querySelector('[data-hero-open-link]');
      const openLabel = heroPlan.querySelector('[data-hero-open-label]');
      const resumeBtn = dashboard.querySelector('[data-hero-resume-btn]');

      if (titleNode) titleNode.textContent = plan.name;
      if (cidrNode) cidrNode.textContent = plan.cidr;
      if (cidrBtn) cidrBtn.dataset.copyValue = plan.cidr;
      if (usageNode) usageNode.textContent = `${plan.summary.address_consumption.toFixed(1)}% used`;
      if (allocNode) allocNode.textContent = numberFormat.format(plan.summary.allocated_addresses);
      if (remNode) remNode.textContent = numberFormat.format(plan.summary.remaining_addresses);
      if (subNode) subNode.textContent = numberFormat.format(plan.summary.subnet_count);
      if (openLink) openLink.href = plan.detail_url;
      if (openLabel) openLabel.textContent = plan.allocations.length ? 'Open plan' : 'Finish allocation';
      if (resumeBtn) {
        resumeBtn.href = plan.detail_url;
        const span = resumeBtn.querySelector('span');
        if (span) span.textContent = `Resume ${plan.name}`;
      }
      if (segBar) {
        segBar.setAttribute('aria-label', `${plan.summary.allocated_addresses} of ${plan.summary.total_addresses} addresses allocated`);
      }

      dashboard.querySelectorAll('[data-switch-project]').forEach(tab => {
        const active = tab.dataset.switchProject === String(plan.id);
        tab.classList.toggle('is-active', active);
        tab.setAttribute('aria-selected', active ? 'true' : 'false');
      });
      dashboard.querySelectorAll('[data-project-row]').forEach(row => {
        const active = row.dataset.projectRow === String(plan.id);
        row.classList.toggle('is-deck-active', active);
        const btn = row.querySelector('[data-preview-project]');
        if (btn) {
          btn.classList.toggle('is-active', active);
          const lbl = btn.querySelector('span');
          if (lbl) lbl.textContent = active ? 'On deck' : 'Preview';
        }
      });

      if (segBar) segBar.replaceChildren();
      if (chipsWrap) chipsWrap.replaceChildren();

      if (!plan.allocations.length) {
        if (emptyNote) emptyNote.hidden = false;
        if (segBar) segBar.hidden = true;
        if (chipsWrap) chipsWrap.hidden = true;
        if (readout) readout.hidden = true;
        return;
      }

      if (emptyNote) emptyNote.hidden = true;
      if (segBar) segBar.hidden = false;
      if (chipsWrap) chipsWrap.hidden = false;

      const getNodeCenterRatio = node => {
        if (!stage || !node) return 0.5;
        const stageRect = stage.getBoundingClientRect();
        const nodeRect = node.getBoundingClientRect();
        if (!stageRect.width) return 0.5;
        return (nodeRect.left - stageRect.left + nodeRect.width / 2) / stageRect.width;
      };

      const segmentNodes = [];
      plan.allocations.forEach((item, index) => {
        const tone = index % 4;
        const segWeight = Math.max(0.16, Math.pow(item.relative_span, 0.58));
        const segBtn = document.createElement('button');
        segBtn.type = 'button';
        segBtn.className = `hero-seg hero-seg--${tone}`;
        segBtn.style.flex = `${segWeight.toFixed(3)} 1 0%`;
        segBtn.dataset.heroSegmentId = String(item.id);
        segBtn.setAttribute('aria-pressed', 'false');
        segBtn.setAttribute('aria-label', `${item.name}, ${item.network}/${item.prefix}, ${item.allocated_addresses} addresses`);
        segBtn.textContent = `/${item.prefix}`;
        segBar?.append(segBtn);
        segmentNodes.push({ id: String(item.id), node: segBtn });

        const pct = (item.relative_span * 100).toFixed(1);
        const showTip = () => showFloatingTooltip(
          tooltip,
          stage,
          getNodeCenterRatio(segBtn),
          -64,
          item.name,
          `${item.network}/${item.prefix}`,
          `${numberFormat.format(item.required_hosts)} / ${numberFormat.format(item.usable_capacity)} hosts · ${pct}%`,
        );

        segBtn.addEventListener('click', () => selectHeroSubnet(plan, item.id, true));
        segBtn.addEventListener('dblclick', () => {
          window.location.href = `${plan.detail_url}?subnet=${item.id}`;
        });
        segBtn.addEventListener('pointerenter', showTip);
        segBtn.addEventListener('pointerleave', () => hideFloatingTooltip(tooltip));
        segBtn.addEventListener('focus', showTip);
        segBtn.addEventListener('blur', () => hideFloatingTooltip(tooltip));
        segBtn.addEventListener('keydown', event => {
          if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
            event.preventDefault();
            const delta = event.key === 'ArrowRight' ? 1 : -1;
            const next = segmentNodes[(index + delta + segmentNodes.length) % segmentNodes.length];
            next.node.focus();
            selectHeroSubnet(plan, next.id, true);
          }
        });

        if (!reducedMotion) {
          segBtn.animate(
            [{ transform: 'scaleX(0.75)', opacity: 0.35 }, { transform: 'scaleX(1)', opacity: 1 }],
            { duration: 340, delay: Math.min(index * 35, 180), easing: 'cubic-bezier(.16,1,.3,1)', fill: 'both' },
          );
        }

        if (chipsWrap) {
          const chip = document.createElement('button');
          chip.type = 'button';
          chip.className = 'hero-subnet-chip';
          chip.dataset.selectHeroSubnet = String(item.id);
          chip.setAttribute('aria-pressed', 'false');
          const lead = document.createElement('span');
          lead.className = 'hero-subnet-chip__lead';
          const dot = document.createElement('span');
          dot.className = `hero-subnet-chip__dot hero-subnet-chip__dot--${tone}`;
          dot.setAttribute('aria-hidden', 'true');
          const strong = document.createElement('strong');
          strong.textContent = item.name;
          lead.append(dot, strong);
          const code = document.createElement('code');
          code.textContent = `${item.network}/${item.prefix}`;
          chip.append(lead, code);
          chip.addEventListener('click', () => selectHeroSubnet(plan, item.id, true));
          chipsWrap.append(chip);
        }
      });

      const usedRatio = Math.min(1, plan.allocations.reduce((sum, item) => sum + item.relative_span, 0));
      const freeRatio = Math.max(0, 1 - usedRatio);
      if (freeRatio > 0.001 && segBar) {
        const freeEl = document.createElement('div');
        freeEl.className = 'hero-seg--free';
        freeEl.style.flex = `${Math.max(0.13, Math.pow(freeRatio, 0.58)).toFixed(3)} 1 0%`;
        freeEl.textContent = freeRatio >= 0.08 ? 'Free' : `+${plan.summary.remaining_addresses}`;
        segBar.append(freeEl);
        const freePct = (freeRatio * 100).toFixed(1);
        freeEl.addEventListener('pointerenter', () => showFloatingTooltip(
          tooltip,
          stage,
          getNodeCenterRatio(freeEl),
          -64,
          'Available address space',
          `${numberFormat.format(plan.summary.remaining_addresses)} addresses free`,
          `${freePct}% unallocated`,
        ));
        freeEl.addEventListener('pointerleave', () => hideFloatingTooltip(tooltip));
      }

      selectHeroSubnet(plan, plan.allocations[0].id, animateSwitch);
      if (animateSwitch && !reducedMotion) {
        heroPlan.animate(
          [{ opacity: 0.72, transform: 'translateY(4px)' }, { opacity: 1, transform: 'translateY(0)' }],
          { duration: 220, easing: 'cubic-bezier(.16,1,.3,1)' },
        );
      }
    };

    dashboard.querySelectorAll('[data-switch-project]').forEach(tab => {
      tab.addEventListener('click', () => {
        const nextPlan = plansById.get(tab.dataset.switchProject);
        if (nextPlan && nextPlan.id !== activePlan.id) renderHeroPlan(nextPlan, true);
      });
    });

    dashboard.querySelectorAll('[data-preview-project]').forEach(btn => {
      btn.addEventListener('click', () => {
        const nextPlan = plansById.get(btn.dataset.previewProject);
        if (!nextPlan) return;
        renderHeroPlan(nextPlan, true);
        heroPlan.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'nearest' });
      });
    });

    renderHeroPlan(activePlan, false);
  };

  const setupPlanningStudio = () => {
    const studio = document.querySelector('[data-planning-studio]');
    const dataNode = document.querySelector('#allocation-visualization-data');
    const map = studio?.querySelector('[data-address-map]');
    const layer = studio?.querySelector('[data-address-segments]');
    const frame = studio?.querySelector('.address-map-frame');
    const tooltip = studio?.querySelector('[data-map-tooltip]');
    if (!studio || !dataNode || !map || !layer || !frame) return;

    let allocations = [];
    try { allocations = JSON.parse(dataNode.textContent); } catch { return; }
    if (!allocations.length) return;
    const byId = new Map(allocations.map(item => [String(item.id), item]));
    const segmentGroups = [];

    allocations.forEach((item, index) => {
      const centerRatio = item.relative_offset + item.relative_span / 2;
      const group = layer.querySelector(`.hero-seg[data-requirement-id="${item.id}"]`);
      if (!group) return;
      segmentGroups.push({ id: String(item.id), group });

      const pct = (item.relative_span * 100).toFixed(1);
      const showThisTip = () => showFloatingTooltip(
        tooltip,
        frame,
        centerRatio,
        -22,
        item.name,
        `${item.network}/${item.prefix}`,
        `${numberFormat.format(item.required_hosts)} / ${numberFormat.format(item.usable_capacity)} hosts · ${pct}% of space`,
      );
      const select = () => selectRequirement(String(item.id), true);

      group.addEventListener('click', select);
      group.addEventListener('pointerenter', showThisTip);
      group.addEventListener('pointerleave', () => hideFloatingTooltip(tooltip));
      group.addEventListener('focus', showThisTip);
      group.addEventListener('blur', () => hideFloatingTooltip(tooltip));
      group.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          select();
        } else if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
          event.preventDefault();
          const delta = event.key === 'ArrowRight' ? 1 : -1;
          const next = segmentGroups[(index + delta + segmentGroups.length) % segmentGroups.length];
          next.group.focus();
          selectRequirement(next.id, true);
        }
      });

      if (!reducedMotion) group.animate(
        [{ opacity: .55 }, { opacity: 1 }],
        { duration: 320, delay: Math.min(index * 40, 200), easing: 'cubic-bezier(.16,1,.3,1)' },
      );
    });

    const remGroup = layer.querySelector('[data-address-remaining]');
    if (remGroup) {
      const usedCount = allocations.reduce((sum, item) => sum + item.allocated_addresses, 0);
      const freeCount = Number(remGroup.textContent.match(/\d+/)?.[0] || 0);
      const totalSpace = usedCount + freeCount;
      const freePct = totalSpace ? ((freeCount / totalSpace) * 100).toFixed(1) : '0.0';
      const remCenter = totalSpace ? usedCount / totalSpace + (freeCount / totalSpace) / 2 : 1;
      remGroup.addEventListener('pointerenter', () => showFloatingTooltip(
        tooltip,
        frame,
        remCenter,
        -22,
        'Available address space',
        `${numberFormat.format(freeCount)} addresses free`,
        `${freePct}% of boundary unallocated`,
      ));
      remGroup.addEventListener('pointerleave', () => hideFloatingTooltip(tooltip));
    }

    function selectRequirement(id, animate = false) {
      const item = byId.get(id);
      if (!item) return;
      studio.querySelectorAll('[data-requirement-id]').forEach(node => {
        const isSelected = String(node.dataset.requirementId) === id;
        node.classList.toggle('is-selected', isSelected);
        if (node.matches('button')) node.setAttribute('aria-pressed', isSelected ? 'true' : 'false');
      });
      studio.querySelectorAll('[data-select-requirement]').forEach(node => {
        node.setAttribute('aria-pressed', String(node.dataset.selectRequirement) === id ? 'true' : 'false');
      });
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
      const copyCidrBtn = studio.querySelector('[data-inspector-copy-cidr]');
      if (copyCidrBtn) {
        copyCidrBtn.dataset.copyValue = `${item.network}/${item.prefix}`;
      }
      const inspector = studio.querySelector('[data-subnet-inspector]');
      const route = studio.querySelector('[data-subnet-route]');
      if (animate && !reducedMotion) {
        if (inspector) {
          inspector.classList.remove('is-switching');
          void inspector.offsetWidth;
          inspector.classList.add('is-switching');
        }
        if (route) {
          route.classList.remove('is-pulsing');
          void route.offsetWidth;
          route.classList.add('is-pulsing');
        }
      }
    }

    const dockButtons = [...studio.querySelectorAll('[data-requirement-list] [data-select-requirement]')];
    dockButtons.forEach((button, index) => {
      button.addEventListener('keydown', event => {
        if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
          event.preventDefault();
          const delta = event.key === 'ArrowDown' ? 1 : -1;
          const next = dockButtons[(index + delta + dockButtons.length) % dockButtons.length];
          next.focus();
          selectRequirement(next.dataset.selectRequirement, true);
        }
      });
    });

    studio.querySelectorAll('[data-select-requirement]').forEach(control => {
      control.addEventListener('click', () => selectRequirement(control.dataset.selectRequirement, true));
    });

    const requestedSubnet = new URLSearchParams(window.location.search).get('subnet');
    if (requestedSubnet && byId.has(String(requestedSubnet))) {
      selectRequirement(String(requestedSubnet), true);
    } else {
      selectRequirement(String(allocations[0].id), false);
    }
  };

  setupMessages();
  setupFormFeedback();
  setupCopyButtons();
  setupBoundaryPreview();
  setupDashboardWorkflow();
  setupDashboardStudio();
  setupPlanningStudio();
})();
