(async (page) => {
  const root = "/Users/logcjj/Documents/GitHub/AI-Hackahton_meituan";
  const outDir = `${root}/goal/goal-9`;
  const failures = [];
  const observations = [];

  const wait = (ms) => page.waitForTimeout(ms);
  const note = (scenario, stage, data) => observations.push({ scenario, stage, data });
  const fail = (scenario, stage, reason, data = {}) => failures.push({ scenario, stage, reason, data });

  async function readState(stage = "") {
    return page.evaluate((stageName) => {
      const visible = (el) => {
        if (!el) return false;
        const style = getComputedStyle(el);
        return style.display !== "none" && style.visibility !== "hidden" && style.opacity !== "0";
      };
      const routeEls = [...document.querySelectorAll(".dispatch-visual.pickup-leg")].filter(visible);
      const routeRows = routeEls.map((el) => ({
        assignment: el.dataset.assignment || "",
        courier: el.dataset.courier || "",
        merchant: el.dataset.merchant || "",
        finalCourier: el.dataset.finalCourier || "",
        d: el.getAttribute("d") || ""
      }));
      const byCourier = routeRows.reduce((acc, row) => {
        if (row.courier) acc[row.courier] = (acc[row.courier] || 0) + 1;
        return acc;
      }, {});
      const frame = document.querySelector(".map-frame");
      const weather = document.querySelector(".weather");
      const detail = document.querySelector(".assignment-detail");
      return {
        stage: stageName,
        selectedLabel: document.querySelector("#case-select option:checked")?.textContent?.trim() || "",
        selectedValue: document.querySelector("#case-select")?.value || "",
        runtime: document.querySelector("#runtime")?.textContent?.trim() || "",
        status: document.querySelector("#status")?.textContent?.trim() || "",
        routeCount: routeRows.length,
        linkCount: [...document.querySelectorAll(".dispatch-link.pickup-leg")].filter(visible).length,
        arrowCount: [...document.querySelectorAll(".dispatch-arrow")].filter(visible).length,
        merchantPins: [...document.querySelectorAll(".pin.merchant")].filter(visible).length,
        courierPins: [...document.querySelectorAll(".pin.courier")].filter(visible).length,
        hitAreas: document.querySelectorAll(".dispatch-hit-area").length,
        oldWeatherRows: document.querySelectorAll(".weather .row, .weather .bar, .weather .weather-bar").length,
        duplicateCouriers: Object.entries(byCourier).filter(([, count]) => count > 1),
        mismatches: routeRows.filter((row) => row.finalCourier && row.finalCourier !== row.courier),
        weatherText: weather ? weather.innerText : "",
        detailText: detail ? detail.innerText : "",
        frameDataset: frame ? { ...frame.dataset } : {},
        mapPanelActive: Boolean(document.querySelector(".map-panel.active")),
        fullscreenButtonActive: Boolean(document.querySelector('[data-map-action="fullscreen"]')?.classList.contains("active")),
        bodyClasses: document.body.className,
        overflow: {
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth,
          scrollHeight: document.documentElement.scrollHeight,
          clientHeight: document.documentElement.clientHeight
        },
        routes: routeRows
      };
    }, stage);
  }

  function curveMidpoint(route) {
    const nums = (route.d.match(/-?\d+(?:\.\d+)?/g) || []).map(Number);
    if (nums.length >= 6) {
      return {
        x: nums[0] * 0.25 + nums[2] * 0.5 + nums[4] * 0.25,
        y: nums[1] * 0.25 + nums[3] * 0.5 + nums[5] * 0.25
      };
    }
    if (nums.length >= 4) return { x: (nums[0] + nums[2]) / 2, y: (nums[1] + nums[3]) / 2 };
    return null;
  }

  async function svgPointToClient(point) {
    return page.evaluate((p) => {
      const svg = document.querySelector(".route-svg");
      const rect = svg.getBoundingClientRect();
      return { x: rect.left + (p.x / 980) * rect.width, y: rect.top + (p.y / 640) * rect.height };
    }, point);
  }

  async function clickRouteAndAssert(scenario, route) {
    const mid = curveMidpoint(route);
    if (!mid) {
      fail(scenario, "route-click", "route has no usable midpoint", route);
      return;
    }
    const client = await svgPointToClient(mid);
    await page.mouse.click(client.x, client.y);
    await wait(180);
    const detail = await page.locator(".assignment-detail").innerText();
    const ok = detail.includes("派单关系：骑手到商家") && detail.includes(route.merchant) && detail.includes(route.courier);
    if (!ok) fail(scenario, "route-click", "route click did not open matching dispatch detail", { route, detail: detail.slice(0, 300), client });
  }

  async function clickPinAndAssert(scenario, selector, expectedKind) {
    const pin = page.locator(selector).first();
    if (!(await pin.count())) {
      fail(scenario, `${expectedKind}-click`, "pin not found", { selector });
      return;
    }
    const box = await pin.boundingBox();
    const entity = await pin.getAttribute("data-entity");
    if (!box || !entity) {
      fail(scenario, `${expectedKind}-click`, "pin missing box or entity", { selector, entity, box });
      return;
    }
    await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
    await wait(180);
    const detail = await page.locator(".assignment-detail").innerText();
    const kindOk = expectedKind === "merchant" ? detail.includes("商家") : detail.includes("骑手");
    if (!kindOk || !detail.includes(entity)) {
      fail(scenario, `${expectedKind}-click`, "pin click did not keep entity detail priority", { entity, detail: detail.slice(0, 300) });
    }
  }

  async function assertFinalState(scenario, state) {
    if (state.runtime !== "00:00:10") fail(scenario, "final", "runtime is not 10 seconds", { runtime: state.runtime });
    if (!state.routeCount) fail(scenario, "final", "no final dispatch routes", state);
    if (state.routeCount !== state.merchantPins) fail(scenario, "final", "route count does not match merchant pins", state);
    if (state.arrowCount !== state.routeCount) fail(scenario, "final", "arrow count does not match route count", state);
    if (state.duplicateCouriers.length) fail(scenario, "final", "duplicate final couriers", state.duplicateCouriers);
    if (state.mismatches.length) fail(scenario, "final", "route courier differs from final courier", state.mismatches);
    if (state.hitAreas !== 0) fail(scenario, "final", "legacy dispatch hit areas returned", { hitAreas: state.hitAreas });
    if (state.oldWeatherRows !== 0) fail(scenario, "final", "legacy weather row/bar structure returned", { oldWeatherRows: state.oldWeatherRows });
    if (state.overflow.scrollWidth > state.overflow.clientWidth + 2) fail(scenario, "final", "page has horizontal overflow", state.overflow);
    if (!state.detailText.includes("派单总览") || !state.detailText.includes("全部商家已自动连线")) {
      fail(scenario, "final", "overview detail missing final dispatch summary", { detail: state.detailText.slice(0, 300) });
    }
  }

  async function auditScenario(config) {
    await page.selectOption("#case-select", { label: config.label });
    await wait(900);
    const switched = await readState("after-scenario-switch");
    note(config.label, "after-scenario-switch", switched);
    if (switched.routeCount !== 0 || switched.arrowCount !== 0) fail(config.label, "switch", "final routes leaked after scenario switch", switched);
    if (switched.detailText.includes("派单总览")) fail(config.label, "switch", "final overview detail leaked after scenario switch", { detail: switched.detailText.slice(0, 260) });

    await page.click("#zoom-in");
    await page.click("#zoom-in");
    await page.click("#reload-cases");
    await wait(900);
    const refreshed = await readState("after-zoom-refresh-position");
    note(config.label, "after-zoom-refresh-position", refreshed);
    if (refreshed.routeCount !== 0 || refreshed.arrowCount !== 0) fail(config.label, "refresh-position", "final routes present after refresh position", refreshed);
    const zoom = Number(refreshed.frameDataset.zoomLevel || "0");
    if (!Number.isFinite(zoom) || zoom > 14.2) fail(config.label, "refresh-position", "refresh position did not reset excessive zoom", { zoom, dataset: refreshed.frameDataset });

    await page.click("#run-agent");
    await page.waitForFunction(() => document.querySelector("#runtime")?.textContent?.trim() === "00:00:10", null, { timeout: 14000 });
    await wait(400);
    const finalState = await readState("final");
    note(config.label, "final", finalState);
    await assertFinalState(config.label, finalState);
    if (config.weatherMustInclude && !finalState.weatherText.includes(config.weatherMustInclude)) {
      fail(config.label, "weather", "weather text does not match scenario", { expected: config.weatherMustInclude, weatherText: finalState.weatherText });
    }

    if (finalState.routes[0]) await clickRouteAndAssert(config.label, finalState.routes[0]);
    await clickPinAndAssert(config.label, ".pin.merchant", "merchant");
    await clickPinAndAssert(config.label, ".pin.courier", "courier");

    await page.click(".strategy");
    await wait(150);
    const strategyDetail = await page.locator(".assignment-detail").innerText();
    if (!strategyDetail.includes("策略详情")) fail(config.label, "strategy-click", "strategy click did not open strategy detail", { detail: strategyDetail.slice(0, 260) });

    await page.click(".table-panel tbody tr");
    await wait(150);
    const tableDetail = await page.locator(".assignment-detail").innerText();
    if (!tableDetail.length) fail(config.label, "table-click", "table click produced empty detail");

    await page.click('[data-map-action="routes"]');
    await wait(150);
    let buttonState = await readState("routes-hidden");
    if (buttonState.frameDataset.routesHidden !== "true") fail(config.label, "routes-toggle", "routes toggle did not set hidden state", buttonState.frameDataset);
    await page.click('[data-map-action="routes"]');
    await page.click('[data-map-action="depots"]');
    await wait(150);
    buttonState = await readState("entities-muted");
    if (buttonState.frameDataset.entitiesMuted !== "true") fail(config.label, "depots-toggle", "entity toggle did not set muted state", buttonState.frameDataset);
    await page.click('[data-map-action="depots"]');
    await page.click('[data-map-action="fit"]');
    await page.click('[data-map-action="locate"]');
    await wait(900);
    buttonState = await readState("after-fit-locate");
    if (buttonState.frameDataset.locating === "true") fail(config.label, "locate", "locating state remained true after one-shot action", buttonState.frameDataset);
    await page.click('[data-map-action="fullscreen"]');
    await wait(250);
    buttonState = await readState("fullscreen-on");
    if (!buttonState.mapPanelActive || buttonState.frameDataset.fullscreen !== "true" || !buttonState.fullscreenButtonActive) {
      fail(config.label, "fullscreen", "fullscreen did not enter map panel focus mode", {
        mapPanelActive: buttonState.mapPanelActive,
        fullscreen: buttonState.frameDataset.fullscreen,
        fullscreenButtonActive: buttonState.fullscreenButtonActive
      });
    }
    await page.click('[data-map-action="fullscreen"]');
    await wait(250);
  }

  await page.setViewportSize({ width: 1280, height: 720 });
  await page.goto("http://127.0.0.1:8765/", { waitUntil: "domcontentloaded" });
  await wait(900);

  const scenarios = [
    { label: "商圈十字路口高峰", weatherMustInclude: "晴朗" },
    { label: "雨天低接单意愿", weatherMustInclude: "雨" },
    { label: "骑手稀缺修复" }
  ];

  for (const scenario of scenarios) {
    try {
      await auditScenario(scenario);
    } catch (error) {
      fail(scenario.label, "exception", error && error.stack ? error.stack : String(error));
    }
  }

  await page.screenshot({ path: `${outDir}/task16-final.png`, scale: "css" });
  const result = {
    generatedAt: new Date().toISOString(),
    failureCount: failures.length,
    failures,
    observations,
    screenshot: "goal/goal-9/task16-final.png"
  };
  await page.evaluate((audit) => {
    window.__TASK16_AUDIT__ = audit;
    document.body.dataset.task16Audit = JSON.stringify(audit);
  }, result);
  return result;
})
