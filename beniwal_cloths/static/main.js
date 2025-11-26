
function getLocationThen(callback){
    if(navigator.geolocation){
        navigator.geolocation.getCurrentPosition(function(pos){
            callback(pos.coords.latitude, pos.coords.longitude);
        }, function(err){
            console.warn('geolocation failed', err);
            callback(0,0);
        });
    } else {
        callback(0,0);
    }
}

function startBuy(productId){
    const phone = document.getElementById('buyer_phone').value.trim();
    if(!phone){ alert('Please enter phone'); return; }
    getLocationThen(function(lat,lon){
        document.getElementById('buyer_lat').value = lat;
        document.getElementById('buyer_lon').value = lon;
        fetch('/buy/' + productId, {
            method:'POST',
            headers:{'Content-Type':'application/x-www-form-urlencoded'},
            body: 'buyer_phone=' + encodeURIComponent(phone) + '&buyer_lat=' + lat + '&buyer_lon=' + lon
        }).then(r=>r.json()).then(data=>{
            if(data.error){ alert(data.error); return; }
            document.getElementById('callNumber').innerText = data.seller_phone || 'No phone';
            window.current_order = data.order_id;
            document.getElementById('callSection').style.display = 'block';
        });
    });
}

function markCallDone(){
    document.getElementById('callSection').style.display = 'none';
    document.getElementById('confirmSection').style.display = 'block';
}

function finalConfirm(choice){
    if(!window.current_order){ alert('No order found'); return; }
    fetch('/confirm/' + window.current_order, {
        method:'POST',
        headers:{'Content-Type':'application/x-www-form-urlencoded'},
        body: 'action=' + choice
    }).then(r=>r.json()).then(data=>{
        alert('Result: ' + JSON.stringify(data));
        window.location = '/';
    });
}
