/* Linked hover between the two education "spending by level" charts.
 *
 * Hovering a year on one chart shows the same year's hover on the other, when
 * that chart has a point at that year; otherwise the other chart's hover is
 * cleared. pages/education.py registers `sync` as a clientside callback on
 * both graphs' hoverData (with clear_on_unhover, so leaving a chart clears
 * its partner too) and figure. A programmatic Plotly.Fx.hover emits no
 * plotly_hover event, so the mirrored chart never echoes back to the source.
 *
 * Both charts also get their unified hover box pinned to the top of the plot
 * area. Plotly centres that box on the hovered points and offers no option to
 * move it, and it redraws the box on every mouse move (with no event when the
 * points are unchanged), so a MutationObserver on each chart container
 * re-pins it whenever Plotly positions it.
 */
(function () {
    var HOVER_TOP_PAD = 4;

    function plotDiv(id) {
        // The chart container and its dcc.Graph share an id; either way the
        // plotly graph div is the (or a) .js-plotly-plot node.
        var el = document.getElementById(id);
        if (!el) return null;
        return el.classList.contains("js-plotly-plot")
            ? el
            : el.querySelector(".js-plotly-plot");
    }

    function hoveredX(hoverData) {
        var points = hoverData && hoverData.points;
        return points && points.length ? points[0].x : null;
    }

    function hasPointAtX(gd, x) {
        return gd._fullData.some(function (trace) {
            if (trace.visible !== true || !trace.x) return false;
            for (var i = 0; i < trace.x.length; i++) {
                if (Number(trace.x[i]) === Number(x)) return true;
            }
            return false;
        });
    }

    // --- Pin the unified hover box to the top of the plot area -------------

    function isHoverBox(node) {
        return !!(node && node.nodeType === 1 && node.matches &&
                  node.matches(".hoverlayer > g.legend"));
    }

    function pinBox(box) {
        var gd = box.closest(".js-plotly-plot");
        var ya = gd && gd._fullLayout && gd._fullLayout.yaxis;
        if (!ya) return;
        var m = /translate\(\s*([-+\d.eE]+)[ ,]+([-+\d.eE]+)\s*\)/.exec(
            box.getAttribute("transform") || ""
        );
        if (!m) return;
        var top = ya._offset + HOVER_TOP_PAD;
        // Keep Plotly's x (left/right of the point); only the y is pinned.
        // A no-op when already there, so re-setting cannot loop the observer.
        if (Math.abs(parseFloat(m[2]) - top) < 0.5) return;
        box.setAttribute("transform", "translate(" + m[1] + "," + top + ")");
    }

    function pinHoverToTop(containerId) {
        var container = document.getElementById(containerId);
        if (!container || container.__hoverPinned) return;
        container.__hoverPinned = true;
        new MutationObserver(function (records) {
            records.forEach(function (record) {
                if (record.type === "attributes") {
                    if (isHoverBox(record.target)) pinBox(record.target);
                } else {
                    record.addedNodes.forEach(function (node) {
                        if (isHoverBox(node)) pinBox(node);
                    });
                }
            });
        }).observe(container, {
            subtree: true,
            childList: true,
            attributes: true,
            attributeFilter: ["transform"],
        });
    }

    // --- Dash clientside entry point ---------------------------------------

    window.dash_clientside = Object.assign({}, window.dash_clientside, {
        linked_hover: {
            // Inputs: hoverData and figure of both charts (any order).
            sync: function () {
                var dc = window.dash_clientside;
                var ctx = dc.callback_context;
                var hoverInputs = (ctx.inputs_list || []).filter(function (input) {
                    return input.property === "hoverData";
                });
                // Idempotent; runs on every trigger (incl. the initial one and
                // new figures) so the box is pinned from the very first hover.
                hoverInputs.forEach(function (input) { pinHoverToTop(input.id); });

                var triggered = (ctx.triggered || []).filter(function (item) {
                    return item.prop_id && item.prop_id !== ".";
                });
                if (triggered.length !== 1) return dc.no_update;
                var propId = triggered[0].prop_id;
                var dot = propId.lastIndexOf(".");
                if (propId.slice(dot + 1) !== "hoverData") return dc.no_update;
                var sourceId = propId.slice(0, dot);

                var source = null;
                var target = null;
                hoverInputs.forEach(function (input) {
                    if (input.id === sourceId) source = input;
                    else target = input;
                });
                var gd = target && plotDiv(target.id);
                if (!source || !gd || !gd._fullData || !window.Plotly) {
                    return dc.no_update;
                }

                var x = hoveredX(source.value);
                if (x !== null && hasPointAtX(gd, x)) {
                    // xval keeps the chart's own hovermode (x unified), which
                    // then shows only the points at exactly this x.
                    window.Plotly.Fx.hover(gd, {xval: x});
                } else {
                    window.Plotly.Fx.unhover(gd);
                }
                return dc.no_update;
            }
        }
    });
})();
