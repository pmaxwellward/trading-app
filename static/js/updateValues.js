let options = {
    method: "POST", 
    headers: { 
      'content-type': 'application/json'}
    }

// recursively update relevant data from route    
async function fetchData () {
  const res = await fetch(window.location.pathname, options);
  const data = await res.json();
  updateValues(data);
  setTimeout(10000, fetchData())
}

fetchData();

// update values in the client side
function updateValues(res) {
  Object.entries(res).forEach(([key, value]) => {
    let el = document.getElementById(key)
    
    let updated = value.toFixed(2);
    
    if(el.classList.contains("pl")) {
      
      if (updated > 0) {

          if(el.classList.contains("is-loss"))
            el.classList.remove("is-loss")

          if (el.classList.contains("usd"))
            updated = "+" + updated;
            
          el.classList.add("is-profit")
            
      } else if (updated < 0 ) {
        //
        if(el.classList.contains("is-profit"))
            el.classList.remove("is-proft")

            el.classList.add("is-loss")

      } else {

        if(el.classList.contains("is-loss") || el.classList.contains("is-profit"))
          el.classList.remove("is-loss")
          el.classList.remove("is-profit")
      }

    }

    if (el.classList.contains("pct"))
      updated = updated + "%";
    
    el.innerText = updated;
    
  });
}