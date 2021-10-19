function postQuote(symbol) {

    // Send POST request to the quote route
    // Note: Flask only renders templates with requests from HTML forms in document

    let form = document.createElement("form")
    let input = document.createElement("input");

    form.setAttribute("method", "post");
    form.setAttribute("action", "/quote");
    form.setAttribute("style", "display: none;")
    form.setAttribute("id", "quote-form");

    input.name = "symbol";
    input.type = "text";
    input.value = symbol;

    form.append(input);

    document.body.appendChild(form);

    document.querySelector("#quote-form").submit()

    // let symbolInput = document.querySelector("#symbol-input");
    // symbolInput.value = symbol;
    // document.querySelector("#quote-form").submit();

}