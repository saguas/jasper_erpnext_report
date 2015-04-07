

function bind_events() {

	$(document).find("#jasper_print").click(function() {
		window.frames["jasper_viewer"].focus();
		window.frames["jasper_viewer"].print();
	});

	$(document).find("#jasper_fullscreen").click(function() {
		var viewer = document.getElementById('jasper_viewer');
		var rFS = viewer.mozRequestFullScreen || viewer.webkitRequestFullscreen || viewer.requestFullscreen;
		rFS.call(viewer);
	});

};

$("#jasper_viewer").ready(function(){
	bind_events();
});

$("#jasper_viewer").css({
	"padding":"10px",
	"padding-top":"30px",
   "background":"#404040",
   "webkit-border-radius": "7px",
   "-moz-border-radius": "7px",
   "border-radius": "7px",
   "margin":"0 auto",
   "overflow":"hidden"
});
