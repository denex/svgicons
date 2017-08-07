// @ts-check
'use strict';
function init() {
    console.info("init");
    const onMessage = function(evt) {
        if (evt.data === "Refresh") {
            ws.close();
            // Reload page
            location.reload();
        } else {
            console.debug("Unknown message:", evt);
        }
    }
    const ws = new WebSocket("ws://localhost:8080/");
    ws.onmessage = function(evt) { onMessage(evt); };
    ws.onopen = function(evt) { console.info("onopen", evt); };
    ws.onclose = function(evt) { console.info("onclose", evt); };
    ws.onerror = function(evt) { console.error("onerror", evt); };
}
window.addEventListener("load", init, false);
