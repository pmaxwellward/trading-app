// update quote results with each keystroke

let search = document.querySelector(".search");

search.focus();

search.addEventListener("keyup", (e) => {
    fetch(`/search?q=${search.value}`)
    .then(res => res.json())
    .then(data => {
        let html = '';
        for (let i = 0; i < data.length; i++) {
            html += 
            `<li class="search-result" onclick="postQuote('${data[i].symbol}')">
                <div class="result-symbol">${data[i].symbol}</div>
                <div class="result-name">${data[i].name}</div>
            </li>`;
        }
        document.querySelector("#symbol-list").innerHTML = html;
    })
    .catch(error => console.error('Error', error));


}); 

