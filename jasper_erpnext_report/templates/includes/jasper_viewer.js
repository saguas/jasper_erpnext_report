

function bind_events() {

	$(document).find("#jasper_print").click(function() {
		window.frames["viewer"].focus();
		window.frames["viewer"].print();
	});

	$(document).find("#jasper_fullscreen").click(function() {
		var viewer = document.getElementById('viewer');
		var rFS = viewer.mozRequestFullScreen || viewer.webkitRequestFullscreen || viewer.requestFullscreen;
		rFS.call(viewer);
	});
};

$("#viewer").css({
	"padding":"10px",
	"padding-top":"30px",
   "background":"#404040",
   "webkit-border-radius": "7px",
   "-moz-border-radius": "7px",
   "border-radius": "7px",
   "margin":"0 auto",
   "overflow":"hidden"
});
