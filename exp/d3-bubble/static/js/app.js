(function() {

	/* Events from UI */

	var SOCKET_ADDR = 'http://' + document.domain + ':' + location.port;


	/* D3 Bubble Chart */

	var diameter = Math.min(document.getElementById('chart').clientWidth, window.innerHeight - document.querySelector('header').clientHeight) - 20;
	// var diameter = document.getElementById('chart').clientWidth;

	var svg = d3.select('#chart').append('svg')
		.attr('width', diameter)
		.attr('height', diameter);

	var bubble = d3.layout.pack()
		.size([diameter, diameter])
		.value(function(d) {return d.size;}) // new data is loaded to bubble layout
		.padding(3);

	function drawBubbles(m) {

		// generate data with calculated layout values
		var nodes = bubble.nodes(processData(m))
			.filter(function(d) { return !d.children; }); // filter out the outer bubble

		console.log(nodes);

		// assign new data to existing DOM 
		var vis = svg.selectAll('circle')
			.data(nodes, function(d) { return d.name; });

		// enter data -> remove, so non-exist selections for upcoming data won't stay -> enter new data -> ...

		// To chain transitions, 
		// create the transition on the updating elements before the entering elements 
		// because enter.append merges entering elements into the update selection

		var duration = 500;
		var delay = 0;

		// update - this is created before enter.append. it only applies to updating nodes.
		vis.transition()
			.duration(duration)
			.delay(function(d, i) {delay = i * 7; return delay;}) 
			.attr('transform', function(d) { return 'translate(' + d.x + ',' + d.y + ')'; })
			.attr('r', function(d) { return d.r; })
			.style('opacity', 1) // force to 1, so they don't get stuck below 1 at enter()
			.select('title').text(function(d) { return d.name+', '+d.size; });

		// enter - only applies to incoming elements (once emptying data)	
		var circles = vis.enter().append('circle')
			.attr('transform', function(d) { return 'translate(' + d.x + ',' + d.y + ')'; })
			.attr('r', function(d) { return 0; })
			.attr('class', function(d) { return d.className; });
		circles.append("svg:title")
   			   .text(function(d) { return d.name+', '+d.size; });  // display tooltip
		circles.transition()
			   .duration(duration * 1.2)
			   .attr('transform', function(d) { return 'translate(' + d.x + ',' + d.y + ')'; })
			   .attr('r', function(d) { return d.r; })
			   .style('opacity', 1);

		// exit
		vis.exit()
			.transition()
			.duration(duration)
			.attr('transform', function(d) { 
				var dy = d.y - diameter/2;
				var dx = d.x - diameter/2;
				var theta = Math.atan2(dy,dx);
				var destX = diameter * (1 + Math.cos(theta) )/ 2;
				var destY = diameter * (1 + Math.sin(theta) )/ 2; 
				return 'translate(' + destX + ',' + destY + ')'; })
			.attr('r', function(d) { return 0; })
			.remove();
	}



	function getData() {
		var socket2 = io.connect(SOCKET_ADDR, {'force new connection':true });
		socket2.emit('word_count_and_stats_c2s', '');
		socket2.on("word_count_and_stats_s2c", function(data) {
			drawBubbles(data);
		});
	}

	function processData(data) {
		if(!data) return;
		data = $.parseJSON(data);
		country_list = Object.keys(data);
		data = data[country_list[0]][1];  // select the first country as exp
		var newDataSet = [];
		for (var i = 0; i < data.length; i++) {
			var pair = data[i];
			// console.log(pair);
			newDataSet.push({name: pair[0], className: "us", size: pair[1]});
		}
		return {children: newDataSet};
	}

	getData();
	
})();