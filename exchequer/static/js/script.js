async function getTransaction(){
  var lookup = $("meta[name='lookup']").attr("content");  
  var base = $("meta[name='base']").attr("content"); 
  // var callback = $("meta[name='base']").attr("content");
  var callback = "http://127.0.0.1/success";
  console.log(lookup);
    axios.get(base + 'client_api/txstat/' + lookup) 
    .then(function (response) {
      var tStat = response.data.transactionStatus;
      if (tStat) {
        document.getElementById("ts").innerHTML = '<svg class="checkmark" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 52 52"><circle class="checkmark__circle" cx="26" cy="26" r="25" fill="none" /><path class="checkmark__check" fill="none" d="M14.1 27.2l7.1 7.2 16.7-16.8" /></svg>'
        // document.getElementById("done").innerHTML = 'true'
        console.log('transaction_found')
        // sleep(7000).then(window.location.replace(callback));
      } else {
        console.log("transaction not found")
        setTimeout(getTransaction, 1000);
      }
    });
      
}

// async function countdown(){
// var lookup = $("meta[name='lookup']").attr("content");  
// console.log(lookup)
// }

console.log("hello");
setTimeout(getTransaction,100);
countdown();

function copyToClipboard(element) {
  var $temp = $("<input>");
  $("body").append($temp);
  $temp.val($(element).text()).select();
  document.execCommand("copy");
  $temp.remove();
}
