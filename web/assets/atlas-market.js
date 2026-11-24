(() => {
  "use strict";

  const instruments = {
    "COINBASE:BTCUSD": "BTC / USD",
    "COINBASE:ETHUSD": "ETH / USD",
    "OANDA:XAUUSD": "Gold / USD",
    "OANDA:EURUSD": "EUR / USD",
    "OANDA:XAGUSD": "Silver / USD",
  };
  const provider = "https://s3.tradingview.com/external-embedding/embed-widget-";
  const widgets = {
    chart: ["advanced-chart", { autosize: true, interval: "60", timezone: "Etc/UTC", style: "1", allow_symbol_change: false, calendar: false }],
    quote: ["symbol-info", { width: "100%" }],
    news: ["timeline", { feedMode: "symbol", width: "100%", height: "100%", displayMode: "regular" }],
  };
  const labels = {
    en: {
      title: "Market desk", market: "Instrument", chart: "Price chart", quote: "Market quote", news: "Market news",
      timing: "Quote timing varies by exchange.", loading: "Opening TradingView…",
      unavailable: "TradingView did not load.", retry: "Retry", open: "Open in TradingView",
    },
    ar: {
      title: "مكتب الأسواق", market: "الأداة المالية", chart: "الرسم البياني", quote: "سعر السوق", news: "أخبار السوق",
      timing: "يختلف توقيت الأسعار حسب البورصة.", loading: "جارٍ فتح TradingView…",
      unavailable: "تعذّر تحميل TradingView.", retry: "إعادة المحاولة", open: "فتح في TradingView",
    },
  };

  function mountWidget(panel, key, symbol, locale, theme, strings) {
    const host = panel.querySelector("[data-tv-host]");
    const status = panel.querySelector("[data-tv-status]");
    const retry = panel.querySelector("button");
    const [widget, options] = widgets[key];
    const embed = document.createElement("div");
    embed.className = "tradingview-widget-container";
    const backdrop = document.createElement("div");
    backdrop.className = "tradingview-widget-container__widget";
    embed.append(backdrop);

    const embedScript = document.createElement("script");
    embedScript.src = provider + widget + ".js";
    embedScript.async = true;
    const themeOption = key === "chart" ? { theme } : { colorTheme: theme };
    embedScript.textContent = JSON.stringify({ ...options, ...themeOption, symbol, locale });

    let observedFrame;
    let timeout;
    const observer = new MutationObserver(() => {
      const iframe = embed.querySelector("iframe");
      if (!iframe || iframe === observedFrame) return;
      observedFrame = iframe;
      iframe.title = strings[key] + " · " + instruments[symbol];
      iframe.addEventListener("load", () => finish(true), { once: true });
    });

    function finish(loaded) {
      clearTimeout(timeout);
      observer.disconnect();
      if (!embed.isConnected) return;
      if (!loaded) host.replaceChildren();
      host.hidden = !loaded;
      status.textContent = loaded ? "" : strings.unavailable;
      retry.hidden = loaded;
    }

    status.textContent = strings.loading;
    retry.hidden = true;
    host.hidden = false;
    observer.observe(embed, { childList: true, subtree: true });
    host.replaceChildren(embed);
    embedScript.addEventListener("error", () => finish(false), { once: true });
    timeout = setTimeout(() => finish(false), 12000);
    embed.append(embedScript);
    return () => {
      clearTimeout(timeout);
      observer.disconnect();
    };
  }

  function initialise(board) {
    const makePanel = (key) => `
      <section class="atlas-market-panel atlas-market-${key}" data-tv-panel="${key}" aria-labelledby="atlas-tv-${key}">
        <h3 id="atlas-tv-${key}" data-market-label="${key}"></h3>
        <div data-tv-host></div>
        <div class="atlas-market-feedback">
          <span data-tv-status role="status"></span>
          <button type="button" data-market-label="retry" hidden></button>
          <a data-tv-link data-market-label="open" target="_blank" rel="noopener noreferrer"></a>
        </div>
      </section>`;
    board.innerHTML = `
      <header class="atlas-market-banner">
        <picture class="atlas-market-art" aria-hidden="true">
          <source media="(max-width: 650px)" srcset="/assets/atlas-tiger-small.webp">
          <img src="/assets/atlas-tiger.webp" width="2560" height="1440" alt="" decoding="async">
        </picture>
        <div class="atlas-market-copy">
          <h2 id="atlas-market-title" data-market-label="title"></h2>
          <p data-market-label="timing"></p>
        </div>
        <div class="atlas-market-control">
          <label for="atlas-instrument" data-market-label="market"></label>
          <select id="atlas-instrument" dir="ltr">${Object.entries(instruments).map(([symbol, name]) =>
            `<option value="${symbol}">${name}</option>`).join("")}</select>
        </div>
      </header>
      <div class="atlas-market-grid">${makePanel("chart")}
        <div class="atlas-market-sidebar">${makePanel("quote")}${makePanel("news")}</div>
      </div>`;

    const select = board.querySelector("select");
    const panels = [...board.querySelectorAll("[data-tv-panel]")];
    const reset = new Map();

    function refresh(onlyPanel) {
      const locale = document.documentElement.lang === "ar" ? "ar" : "en";
      const theme = document.documentElement.dataset.theme === "light" ? "light" : "dark";
      const symbol = select.value;
      const strings = labels[locale];
      for (const node of board.querySelectorAll("[data-market-label]")) {
        node.textContent = strings[node.dataset.marketLabel];
      }
      for (const panel of onlyPanel ? [onlyPanel] : panels) {
        const key = panel.dataset.tvPanel;
        const path = "symbols/" + symbol.replace(":", "-") + (key === "news" ? "/news/" : "/");
        const destination = key === "chart" ? "chart/?symbol=" + encodeURIComponent(symbol) : path;
        panel.querySelector("[data-tv-link]").href = "https://www.tradingview.com/" + destination;
        reset.get(key)?.();
        reset.set(key, mountWidget(panel, key, symbol, locale, theme, strings));
      }
    }

    select.addEventListener("change", () => refresh());
    for (const panel of panels) {
      panel.querySelector("button").addEventListener("click", () => refresh(panel));
    }
    new MutationObserver(() => refresh()).observe(document.documentElement, {
      attributes: true, attributeFilter: ["lang", "data-theme"],
    });
    refresh();
  }

  for (const board of document.querySelectorAll("[data-atlas-market]")) initialise(board);
})();
