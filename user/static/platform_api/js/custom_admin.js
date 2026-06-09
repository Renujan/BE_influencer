/* ============================================================
   CUSTOM WAGTAIL ADMIN JS
   Platform Admin UI — Dynamic Widgets & Status Enhancements
   ============================================================ */

(function () {
  'use strict';

  /* ─── Helpers ─────────────────────────────────────────── */

  function ready(fn) {
    if (document.readyState !== 'loading') {
      fn();
    } else {
      document.addEventListener('DOMContentLoaded', fn);
    }
  }

  function qs(sel, ctx) {
    return (ctx || document).querySelector(sel);
  }

  function qsa(sel, ctx) {
    return Array.from((ctx || document).querySelectorAll(sel));
  }

  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html !== undefined) e.innerHTML = html;
    return e;
  }

  /* ─── 1. Inject Status Badge Styles ───────────────────── */

  var STATUS_MAP = {
    'approved':          { cls: 'green',  dot: '●', label: 'Approved' },
    'live':              { cls: 'green',  dot: '●', label: 'Live' },
    'completed':         { cls: 'green',  dot: '●', label: 'Completed' },
    'verified':          { cls: 'green',  dot: '●', label: 'Verified' },
    'active':            { cls: 'green',  dot: '●', label: 'Active' },
    'resolved':          { cls: 'blue',   dot: '●', label: 'Resolved' },
    'closed':            { cls: 'blue',   dot: '●', label: 'Closed' },
    'contract check':    { cls: 'blue',   dot: '●', label: 'Contract Check' },
    'pending':           { cls: 'amber',  dot: '●', label: 'Pending' },
    'in review':         { cls: 'amber',  dot: '●', label: 'In Review' },
    'under review':      { cls: 'amber',  dot: '●', label: 'Under Review' },
    'revision requested':{ cls: 'amber',  dot: '●', label: 'Revision Requested' },
    'draft':             { cls: 'amber',  dot: '●', label: 'Draft' },
    'rejected':          { cls: 'red',    dot: '●', label: 'Rejected' },
    'dispute':           { cls: 'red',    dot: '●', label: 'Dispute' },
    'failed':            { cls: 'red',    dot: '●', label: 'Failed' },
    'safety compliance': { cls: 'purple', dot: '●', label: 'Safety Compliance' },
  };

  var COLOR_STYLES = {
    green:  'background:rgba(34,197,94,0.12);color:#22c55e;border:1px solid rgba(34,197,94,0.25)',
    blue:   'background:rgba(59,130,246,0.12);color:#3b82f6;border:1px solid rgba(59,130,246,0.25)',
    amber:  'background:rgba(245,158,11,0.12);color:#f59e0b;border:1px solid rgba(245,158,11,0.25)',
    red:    'background:rgba(239,68,68,0.10);color:#ef4444;border:1px solid rgba(239,68,68,0.2)',
    purple: 'background:rgba(168,85,247,0.12);color:#a855f7;border:1px solid rgba(168,85,247,0.25)',
  };

  function makeBadge(text, colorKey) {
    var validColors = ['green', 'blue', 'amber', 'red', 'purple'];
    var cls = validColors.indexOf(colorKey) !== -1 ? colorKey : 'amber';
    
    var badge = el('span');
    badge.className = 'platform-status-badge platform-status-badge--' + cls;
    badge.setAttribute('role', 'status');
    badge.setAttribute('aria-label', text);
    
    var dot = el('span');
    dot.setAttribute('style', 'font-size:8px;line-height:1;');
    dot.setAttribute('aria-hidden', 'true');
    dot.textContent = '●';
    badge.appendChild(dot);
    
    var label = el('span');
    label.textContent = text;
    badge.appendChild(label);
    
    return badge;
  }

  function enhanceStatusCells() {
    var cells = qsa('td');
    cells.forEach(function (td) {
      // Safety check: do not double-enhance
      if (td.getAttribute('data-badge-enhanced') === 'true' || td.querySelector('.platform-status-badge')) {
        return;
      }
      var text = td.textContent.trim();
      var key = text.toLowerCase();
      if (STATUS_MAP[key]) {
        var info = STATUS_MAP[key];
        td.innerHTML = '';
        td.setAttribute('data-badge-enhanced', 'true');
        td.style.padding = '10px 16px';
        td.appendChild(makeBadge(info.label, info.cls));
      }
    });
  }

  /* ─── 2. Emoji Prefixes for Row Titles ────────────────── */

  var EMOJI_MAP = [
    { match: /campaign/i,    emoji: '🧴' },
    { match: /compliance/i,  emoji: '🛡️' },
    { match: /user|profile/i,emoji: '👤' },
    { match: /payment/i,     emoji: '💳' },
    { match: /milestone/i,   emoji: '🏁' },
    { match: /workspace/i,   emoji: '📁' },
    { match: /deliverable/i, emoji: '📦' },
    { match: /ticket/i,      emoji: '🎫' },
    { match: /escrow/i,      emoji: '🔐' },
  ];

  function addEmojiPrefixes() {
    var firstCells = qsa('tbody td:first-child');
    firstCells.forEach(function (td) {
      // Safety check: do not double-enhance
      if (td.getAttribute('data-emoji-enhanced') === 'true') {
        return;
      }
      var text = td.textContent.trim();
      // Don't double-prefix
      var hasEmoji = false;
      try {
        hasEmoji = /^(?:[\u2600-\u27BF]|[\uD83C-\uD83E][\uDC00-\uDFFF])/i.test(text);
      } catch (e) {
        // Fallback
      }
      if (hasEmoji) return;
      for (var i = 0; i < EMOJI_MAP.length; i++) {
        if (EMOJI_MAP[i].match.test(text)) {
          var wrapper = el('span');
          wrapper.style.cssText = 'display:flex;align-items:center;gap:7px;';
          var emojiSpan = el('span');
          emojiSpan.style.cssText = 'font-size:14px;flex-shrink:0;';
          emojiSpan.textContent = EMOJI_MAP[i].emoji;
          var textSpan = el('span');
          textSpan.textContent = text;
          textSpan.style.cssText = 'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
          wrapper.appendChild(emojiSpan);
          wrapper.appendChild(textSpan);
          td.innerHTML = '';
          td.setAttribute('data-emoji-enhanced', 'true');
          td.appendChild(wrapper);
          break;
        }
      }
    });
  }

  /* ─── 3. Summary Stats Cards ───────────────────────────── */

  function injectSummaryCards(container) {
    if (document.querySelector('.admin-summary-cards')) {
      return; // Already injected!
    }
    
    var pathname = window.location.pathname;
    var cards = [];
    
    // Resolve dynamic data from window.platformStats injected from db by wagtail_hooks.py
    var stats = window.platformStats || {
      tickets: { total: 0, pending: 0, approved: 0, resolved: 0 },
      campaigns: { total: 0, live: 0, completed: 0, pending: 0 },
      users: { total: 0, creators: 0, brands: 0, superadmins: 0 }
    };

    if (/compliance|ticket/i.test(pathname)) {
      cards = [
        { label: 'Total Tickets',   value: stats.tickets.total,   sub: 'All time tickets' },
        { label: 'Pending Review',  value: stats.tickets.pending,  sub: 'Awaiting review' },
        { label: 'Approved',        value: stats.tickets.approved, sub: 'Approved compliance' },
        { label: 'Resolved',        value: stats.tickets.resolved, sub: 'Closed disputes' }
      ];
    } else if (/campaign/i.test(pathname)) {
      cards = [
        { label: 'Total Campaigns',  value: stats.campaigns.total, sub: 'All workspaces' },
        { label: 'Live',             value: stats.campaigns.live, sub: 'Active campaign threads' },
        { label: 'Completed',        value: stats.campaigns.completed, sub: 'Finished cycles' },
        { label: 'Pending Requests',  value: stats.campaigns.pending, sub: 'Under verification' }
      ];
    } else if (/user_profiles|userprofile|user/i.test(pathname)) {
      cards = [
        { label: 'Total Users',    value: stats.users.total, sub: 'Registered accounts' },
        { label: 'Creators',       value: stats.users.creators, sub: 'Influencer creators' },
        { label: 'Brands',         value: stats.users.brands, sub: 'Businesses enrolled' },
        { label: 'Super Admins',   value: stats.users.superadmins, sub: 'System administrators' }
      ];
    }

    if (!cards.length) return;

    var grid = el('div', 'admin-summary-cards');
    cards.forEach(function (c) {
      var card = el('div', 'admin-summary-card');
      card.innerHTML =
        '<div class="admin-summary-card__label">' + c.label + '</div>' +
        '<div class="admin-summary-card__value">' + c.value + '</div>' +
        '<div class="admin-summary-card__sub">' + c.sub + '</div>';
      grid.appendChild(card);
    });

    container.insertAdjacentElement('beforebegin', grid);
  }

  /* ─── 4. Platform Activity Timeline ────────────────────── */

  var TIMELINE_EVENTS = [
    {
      icon: '📁',
      iconBg: 'rgba(59,130,246,0.15)',
      title: 'Campaign Workspace Launched',
      desc: 'Acme Corp initialized Summer Drop 2026 workspace.',
      time: '10 mins ago'
    },
    {
      icon: '🔐',
      iconBg: 'rgba(34,197,94,0.15)',
      title: 'Escrow Deposit Funded',
      desc: 'Vertex Brand funded Campaign milestone ($1,500.00).',
      time: '1 hour ago'
    }
  ];

  function injectTimeline(targetEl) {
    if (document.querySelector('.activity-timeline')) {
      return; // Already injected
    }
    
    var stats = window.platformStats || {};
    var events = stats.timeline || TIMELINE_EVENTS;
    
    var section = el('div', 'activity-timeline');

    var heading = el('h3', 'activity-timeline__heading');
    heading.innerHTML = '<span style="color:#ff7a45;">⚡</span> Platform Activity Timeline';
    section.appendChild(heading);

    var list = el('ul', 'activity-timeline__list');

    events.forEach(function (evt) {
      var item = el('li', 'activity-timeline__item');

      var iconDiv = el('div', 'activity-timeline__icon');
      iconDiv.style.background = evt.iconBg;
      iconDiv.textContent = evt.icon;

      var body = el('div', 'activity-timeline__body');

      var title = el('p', 'activity-timeline__title');
      title.textContent = evt.title;

      var desc = el('p', 'activity-timeline__desc');
      desc.textContent = evt.desc;

      var time = el('span', 'activity-timeline__time');
      time.textContent = evt.time;

      body.appendChild(title);
      body.appendChild(desc);
      body.appendChild(time);

      item.appendChild(iconDiv);
      item.appendChild(body);
      list.appendChild(item);
    });

    section.appendChild(list);
    targetEl.appendChild(section);
  }

  /* ─── 5. Compliance Progress Bars ─────────────────────── */

  function injectProgressWidget(targetEl) {
    if (document.querySelector('.compliance-progress')) {
      return; // Already injected
    }
    
    var stats = window.platformStats || {
      compliance: { auditRate: 87, escrowCoverage: 94, disputeSpeed: 72, creatorAuth: 81 }
    };
    var comp = stats.compliance || {};

    var progressItems = [
      { name: 'Platform Audit Status',       pct: comp.auditRate || 0, variant: '' },
      { name: 'Escrow Coverage',             pct: comp.escrowCoverage || 0, variant: 'green' },
      { name: 'Dispute Resolution Speed',    pct: comp.disputeSpeed || 0, variant: 'blue' },
      { name: 'Creator Authentication Rate', pct: comp.creatorAuth || 0, variant: '' },
    ];
    
    var widget = el('div', 'compliance-progress');

    var heading = el('h3', 'compliance-progress__heading');
    heading.textContent = 'Compliance Health';
    widget.appendChild(heading);

    progressItems.forEach(function (item) {
      var row = el('div', 'compliance-progress__item');

      var labelRow = el('div', 'compliance-progress__label');
      var name = el('span', 'compliance-progress__name');
      name.textContent = item.name;
      var pct = el('span', 'compliance-progress__pct');
      pct.textContent = item.pct + '%';
      labelRow.appendChild(name);
      labelRow.appendChild(pct);

      var barBg = el('div', 'compliance-progress__bar-bg');
      var fill = el('div',
        'compliance-progress__bar-fill' +
        (item.variant ? ' compliance-progress__bar-fill--' + item.variant : '')
      );
      fill.style.width = '0%';
      barBg.appendChild(fill);

      row.appendChild(labelRow);
      row.appendChild(barBg);
      widget.appendChild(row);

      // Animate width after paint
      requestAnimationFrame(function () {
        setTimeout(function () {
          fill.style.width = item.pct + '%';
        }, 200);
      });
    });

    targetEl.appendChild(widget);
  }

  /* ─── 6. Find the best insert target ──────────────────── */

  function findInsertTarget() {
    var selectors = [
      '.listing',
      '.w-listing',
      '[class*="index-results"]',
      '.content-inner',
      '.w-content-inner',
      '.page-content',
      'main',
      '[role="main"]',
    ];
    for (var i = 0; i < selectors.length; i++) {
      var found = qs(selectors[i]);
      if (found) return found;
    }
    return document.body;
  }

  /* ─── 7. Main Init ─────────────────────────────────────── */

  ready(function () {
    // Enhance status cells
    enhanceStatusCells();

    // Add emoji prefixes
    addEmojiPrefixes();

    // Find main content container
    var target = findInsertTarget();

    // Inject summary cards before the listing
    injectSummaryCards(target);

    // Inject timeline and progress widgets
    var widgetContainer = el('div', 'dashboard-bottom-grid');

    // On compliance page, show both widgets side by side
    var pathname = window.location.pathname;
    if (/compliance|ticket/i.test(pathname)) {
      var leftCol = el('div');
      var rightCol = el('div');
      injectTimeline(leftCol);
      injectProgressWidget(rightCol);
      widgetContainer.appendChild(leftCol);
      widgetContainer.appendChild(rightCol);
      target.appendChild(widgetContainer);
    } else {
      // Other pages: full-width timeline
      injectTimeline(target);
    }

    // Re-run status enhancement after DOM settles
    setTimeout(enhanceStatusCells, 500);

    // Watch exclusively for AJAX list structural node updates (Highly scoped for performance)
    if (window.MutationObserver) {
      var observer = new MutationObserver(function (mutations) {
        var hasRelevant = mutations.some(function (m) {
          return m.addedNodes.length > 0;
        });
        if (hasRelevant) {
          enhanceStatusCells();
          addEmojiPrefixes();
        }
      });
      observer.observe(document.body, { 
        childList: true, 
        subtree: true 
      });
    }
  });

})();
