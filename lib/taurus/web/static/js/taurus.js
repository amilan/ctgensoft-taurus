// Generated by CoffeeScript 1.3.3
(function() {
    var initialize, initialize_taurus, taurus_element, taurus_models, taurus_websocket;

    taurus_websocket = null;

    taurus_models = function() {
        var elem, _i, _len, _ref, _results;
        _ref = $('[data-taurus-model]');
        _results = [];

        for (_i = 0, _len = _ref.length; _i < _len; _i++) {
            elem = _ref[_i];
            _results.push(elem.dataset['taurusModel']);
        }
        console.log(_results);
        return _results;
    };

    taurus_element = function(model) {

        return $('[data-taurus-model="' + model + '"]');
    };

    initialize = function() {
        console.log("Initializing page...");
        host = "pcvdimper.esrf.fr";
        port = 8888;
        ws_id = "/taurus";
        console.log(host);
        taurus_websocket = new WebSocket("ws://" + host + ":" + port + ws_id);
        taurus_websocket.onopen = function() {
            console.log("Websocket connected");
            return initialize_taurus();
        };
        taurus_websocket.onmessage = function(event) {
            var elements, event_data;
            var reg = new RegExp("[^a-zA-Z0-9_]", "g");
            event_data = JSON.parse(event.data);

            elements = taurus_element(event_data.model);
            elements.each(function(index, elem) {
                //test if the attribute exist and if the string contains only authorized characters
                if ($(elem).attr('data-taurus-function') !== undefined && reg.test($(elem).attr('function')) === false)
                {
                    console.log("window." + $(elem).attr('data-taurus-function') + "()");
                    eval("window." + $(elem).attr('data-taurus-function') + "(event_data,elem)");
                }
                else
                {
                    elements.css(event_data.css).html(event_data.html);
                }
            });
            return;
        };
        taurus_websocket.onerror = function(event) {
            return $('body').append('<div>Error:' + event + ' ' + '</div>');
        };
        taurus_websocket.onclose = function(event) {
            var reg = new RegExp("[^a-zA-Z0-9_]", "g");
            var elements = $('[data-taurus-model]');
            elements.each(function(index, elem) {
                //test if the attribute exist and if the string contains only authorized characters
                if ($(elem).attr('data-taurus-onclose') !== undefined && reg.test($(elem).attr('function')) === false)
                {
                    console.log("window." + $(elem).attr('data-taurus-onclose') + "()");
                    eval("window." + $(elem).attr('data-taurus-onclose') + "(event_data,elem)");
                }
                else
                {
                    elements.html("-");
                }
            });
            console.log("Websocket DISCONNECTED");
        };
        return console.log("Finished initializing page");
    };

    initialize_taurus = function() {

        var json_models, models;
        console.log("Initializing taurus...");
        models = taurus_models();
        json_models = JSON.stringify({
            models: models
        });
        taurus_websocket.send(json_models);
        return console.log("Finished initializing taurus");
    };

    $(function() {
        return initialize();
    });

}).call(this);
