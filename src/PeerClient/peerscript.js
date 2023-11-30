const mediaAvailabilityMap = new Map();
var selected_id = ""

//Initialization of the HTML page
function initApp() {
  
    // Install built-in polyfills to patch browser incompatibilities.
  shaka.polyfill.installAll();
  
  // Check to see if the browser supports the basic APIs Shaka needs.
  if (shaka.Player.isBrowserSupported()) {
    // Everything looks good!
    //force first refresh of available medias on startup
    refreshCallback()
    initPlayer();
  } else {
    // This browser does not have the minimum set of APIs we need.
    console.error('Browser not supported!');
  }
  
}

//Create the Shaka Player and attach it to video element of the HTML page
async function initPlayer() {
  // Create a Player instance.
  const video = document.getElementById('video');
  const player = new shaka.Player(video);

  // Attach player to the window to make it easy to access in the JS console.
  window.player = player;

  // Listen for error events.
  player.addEventListener('error', onErrorEvent);
   
  //Register Response Filter for Peer logic
  player.getNetworkingEngine().registerResponseFilter(peerResponseFilter);

}

// PeerClient - PeerServer communication : farward media segments to PeerServer
function peerResponseFilter(type, response) {
    console.log('PEER_FILTER: responce intercepted :)');
    if(type == shaka.net.NetworkingEngine.RequestType.SEGMENT){ //type == SEGMENT
        
        //prepare body data for PeerServer
        const peerData = {}
        peerData.segmentName = "/MEDIA/" + response.uri.split(/\/MEDIA\//,2)[1];
        peerData.segment = shaka.util.Uint8ArrayUtils.toBase64(new Uint8Array(response.data));
        const peerJson = JSON.stringify(peerData);
        
        fetch_addr = "http://" + window.configParam.PEER_ADDRESS + "/ADD_SEGMENT";
        
        fetch(fetch_addr, {
            method: 'POST' ,
            mode : 'no-cors',
            headers: {
                'Content-Type' :  "application/json"
            } ,
            body : peerJson
        }).then( resp => {
            //console.log('Segment sent to server with reply ' + resp.status.toString() + " " + resp.statusText);
        });
        
    }
}

// ERROR handler functions
function onErrorEvent(event) {
  // Extract the shaka.util.Error object from the event.
  onError(event.detail);
}
function onError(error) {
  // Log the error.
  console.error('ERROR code:', error.code, 'object', error);
}

// Load media from MPD url
async function loadMedia(url) {
    
    //First try to unload previously loaded media (if exists)
    try {
        await player.unload();
        // This runs if the asynchronous load is successful.
        console.log('Unloaded previus media!');
    } catch (e) {
        // onError is executed if the asynchronous load fails.
        onError(e);
    }
    // Then try to load a manifest.
    try {
        await player.load(url);
        // This runs if the asynchronous load is successful.
        console.log('The video has now been loaded!');
    } catch (e) {
        // onError is executed if the asynchronous load fails.
        onError(e);
    }
    
}

//Realize special style for currently selected media
function styleSelectedMedia(){
    
    el = document.getElementById(selected_id);
    el.style= "background-color: #f44336;color: white;";
}


//callback for onCLick event 
async function clickCallback(media,id){
    console.log("INSIDE OnClick!, media is " + media);
    if (!mediaAvailabilityMap.has(media)) {
        console.log("ERROR: On Click for non existing media");
    }
    else {
        
        div = document.getElementById("idURL");
        //restyle div to show which film is currently selected
        if(selected_id != ""){
            //remove special style from previously selected div
            el = document.getElementById(selected_id);
            el.style = ""
        }
        else { 
            //show video element
            el = document.getElementById("idVideoDiv");
            el.style.display = "block";
            div.style.display = "block";
        }
        
        
        div.innerHTML = mediaAvailabilityMap.get(media);
        
        //load media into shaka player
        await loadMedia(mediaAvailabilityMap.get(media));
        
        selected_id = id;
        //console.log("selected id is " + selected_id + " inside clickCallback")
        styleSelectedMedia();
    }
    

}

// Dynamically generate the list of <div> showing which movies is available and which not 
async function refreshCallback(){
    div = document.getElementById("idMovieList");
    
    //async fetch return a promise
    fetch_addr = "http://" + window.configParam.CS_ADDRESS + "/GET_AVAILABLE_MEDIA";
    //fetch('http://localhost:8080/GET_AVAILABLE_MEDIA')
    fetch(fetch_addr)
    .then(response => response.json())
    .then(data => {
        
        //fill table
        for (media in data) {
            mediaAvailabilityMap.set(media, data[media]);
        }
        
        //show results
        html_text = "";
        index = 1;
        to_restyle = true;
        if (selected_id == "") to_restyle = false;
        
        mediaAvailabilityMap.forEach(function(value, key){
                if(value != "NO"){  //media is available
                    html_text += "<div class='item' id='ID_" + index + "' onclick='clickCallback(\"" + key + "\",\"ID_" + index + "\");'>" + key + "</div>";
                    //console.log(value + "" + key);
                }
                else { //media not available
                    html_text += "<div class='item' id='ID_" + index + "' style=\"background-color: #DCDCDC; color: grey; cursor: not-allowed;\">" + key + "</div>";
                    console.log(value + "" + key);
                    if (selected_id == "ID_" + index) {
                        //previously selected is now not available
                        //hide video element related divs
                        el = document.getElementById("idVideoDiv");
                        el.style.display = "none";
                        el = document.getElementById("idURL");
                        el.style.display = "none";
                        //console.log("DEBUG: previously selected is now not available")
                        to_restyle = false;  
                        selected_id = "";
                    }
                    //console.log("media " + key + " not available!")
                }
                index++;
            
        });
        div.innerHTML = html_text;
        
        //special style for currently selected media, has to restyle because we resetted its style while generating divs
        if (to_restyle){
            styleSelectedMedia()
        }
        
    }); //fetc->then->then  
    
}

document.addEventListener('DOMContentLoaded', initApp);

