


// npm install crypto-js
// Import CryptoJS library (if using npm)
// const CryptoJS = require('crypto-js');

// Function to encrypt and store data in localStorage
async function encryptAndStore(key, data) {
  const encryptedData = CryptoJS.AES.encrypt(JSON.stringify(data), key).toString();
  await storeItem(encryptedData, 'encryptedData');
  // localStorage.setItem('encryptedData', encryptedData);
}

// Function to retrieve and decrypt data from localStorage
async function retrieveAndDecrypt(key) {
  
  const encryptedData = await getItem('encryptedData');
  if (encryptedData) {
    const decryptedBytes = CryptoJS.AES.decrypt(encryptedData, key);
    const decryptedData = JSON.parse(decryptedBytes.toString(CryptoJS.enc.Utf8));
    return decryptedData;
  }
  return null;
}

// // Example usage
// const secretKey = 'super-secret-key';
// const dataToStore = { username: 'john_doe', password: 'secure_password' };

// // Encrypt and store data
// encryptAndStore(secretKey, dataToStore);

// // Retrieve and decrypt data
// const retrievedData = retrieveAndDecrypt(secretKey);
// console.log(retrievedData);


// $('#result').html("<br />$('form').serialize():<br />"+ $('form').serialize()+"<br /><br />$('form').serializeArray():<br />" + JSON.stringify($('form').serializeArray()));

// <html>
// <head>
// <script src="http://code.jquery.com/jquery-git2.js"></script>
// <meta charset=utf-8 />
// <title>JS Bin</title>
// </head>
// <body>
//   <form>
//     <input type="radio" name="foo" value="1" checked="checked" />
//     <input type="radio" name="foo" value="0" />
//     <input name="bar" value="xxx" />
//     <select name="this">
//       <option value="hi" selected="selected">Hi11</option>
//       <option value="ho">Ho11</option>
//     </select>
//   </form>
//   <div id=result></div>
// </body>
// </html>

async function connect_to_node2(url, payload = null) {
  console.log('Connecting to node2:', url);
  try {
    const options = {};

    if (payload) {
      options.method = 'POST';
      options.headers = { 'Content-Type': 'application/json' };
      options.body = JSON.stringify(payload);
    }

    const response = await fetch(url, options);

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }
    // console.log('Response status:', response);
    // Try JSON first, fall back to text
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      console.log('Connecting to node json:', response.json());
      return await response.json();
    } else {
      console.log('Connecting to node json:', response.text());
      return await response.text();
    }

  } catch (err) {
    console.error('Connecting to node failed:', err);
    throw err;  // rethrow so caller can handle
  }
}

async function connect_to_node(url, payload = null) {
  console.log('Connecting to node:', url, 'payload',payload);
  try {
    const options = {};

    if (payload) {
      options.method = 'POST';
      options.headers = { 'Content-Type': 'application/json' };
      options.body = JSON.stringify(payload);
    }

    const response = await fetch(url, options);
    if (!response.ok) throw new Error(`Server error: ${response.status}`);

    const contentType = response.headers.get('content-type') || '';

    const body = contentType.includes('application/json')
      ? await response.json()
      : await response.text();

    return body;

  } catch (err) {
    console.error('Request failed:', err);
    throw err;
  }
}




function storeItem(value, key) {
  console.log("Storing item:", key, value);
  return openDatabase().then((db) => {
    return new Promise((resolve, reject) => {
      const tx = db.transaction('keys', 'readwrite');
      tx.objectStore('keys').put(value, key);
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
  });
}

function getItem(key) {
  console.log("Retrieving item:", key);
  return openDatabase().then((db) => {
    return new Promise((resolve, reject) => {
      const tx = db.transaction('keys', 'readonly');
      const getReq = tx.objectStore('keys').get(key);
      getReq.onsuccess = () => resolve(getReq.result);
      getReq.onerror = () => reject(getReq.error);
    });
  });
}
function openDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('KeyDB', 1);

    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains('keys')) {
        db.createObjectStore('keys');
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

// function storeItem(key, name) {
//   return new Promise((resolve, reject) => {
//       const request = indexedDB.open('KeyDB', 1);
//       request.onupgradeneeded = () => {
//       request.result.createObjectStore('keys');
//       };
//       request.onsuccess = () => {
//       const db = request.result;
//       if (!db.objectStoreNames.contains('keys')) {
//         db.createObjectStore('keys');
//       }
//       const tx = db.transaction('keys', 'readwrite');
//       tx.objectStore('keys').put(key, name);
//       tx.oncomplete = () => resolve();
//       tx.onerror = () => reject(tx.error);
//       };
//       request.onerror = () => reject(request.error);
//   });
// }


// function getItem(name) {
//   return new Promise((resolve, reject) => {
//       const request = indexedDB.open('KeyDB', 1);
//       request.onsuccess = () => {
//       const db = request.result;
//       if (!db.objectStoreNames.contains('keys')) {
//         db.createObjectStore('keys');
//       }
//       const tx = db.transaction('keys', 'readonly');
//       const getRequest = tx.objectStore('keys').get(name);
//       getRequest.onsuccess = () => resolve(getRequest.result);
//       getRequest.onerror = () => reject(getRequest.error);
//       };
//       request.onerror = () => reject(request.error);
//   });
// }

function generate_mnemonic() {
  // import { generateMnemonic } from 'https://cdn.skypack.dev/@scure/bip39';
  // import { wordlist } from 'https://cdn.skypack.dev/@scure/bip39/wordlists/english';

  const strength = 256; // 24-word mnemonic
  const mnemonic = generateMnemonic(wordlist, strength);
  console.log("Mnemonic (24 words):", mnemonic);
  return mnemonic
}


function deriveKey(user_id, user_pass) {
  const saltHex = CryptoJS.SHA256(user_pass + ":" + user_id).toString(CryptoJS.enc.Hex);
  console.log("saltHex:", saltHex);
  const saltBytes = Uint8Array.from(saltHex.match(/.{1,2}/g).map(b => parseInt(b, 16)));
  return new Promise((resolve, reject) => {
      scrypt(user_pass, saltBytes, {
      N: 262144,
      r: 8,
      p: 1,
      dkLen: 32,
      encoding: 'hex'
      }, function (derivedKeyHex) {
      resolve(derivedKeyHex);
      });
  })
}

async function getKeyPair(user_id, user_pass) {

  const seedHex = await deriveKey(user_id, user_pass);
  console.log("Derived Seed (Hex):", seedHex);

  const ec = new elliptic.ec('secp256k1');
  const keyPair = ec.keyFromPrivate(seedHex);

  const privKeyHex = keyPair.getPrivate("hex");
  const pubKeyHex = keyPair.getPublic().encode("hex"); // uncompressed

  console.log("Private Key:", privKeyHex);
  console.log("Public Key:", pubKeyHex);
  
  // await storeKey(privKeyHex, 'private');
  // await storeKey(pubKeyHex, 'public');

  // encrypt/decrypt
  // const message = {'test_dict':'this is a test'};
  // const encryptedData = encryptMessage(pubKeyHex, keyPair, JSON.stringify(message));
  // const jx = JSON.stringify(encryptedData)
  // console.log('Encrypted Data:', jx);

  // const decryptedMessage = decryptMessage(privKeyHex, pubKeyHex, JSON.parse(jx));
  // console.log('Decrypted Message:', decryptedMessage);
  
  return [privKeyHex, pubKeyHex];
}

async function sign_new2(data, privKeyHex=null) {
  if (privKeyHex == null) {
    const privKeyHex = await getKey('private');
  }

  hashed_data = await hashMessage(data)
  // const hashed_data = CryptoJS.SHA256(data).toString(CryptoJS.enc.Hex);
  console.log('hashed_data',hashed_data)
  const curve = new elliptic.ec('secp256k1');
  let keys = curve.keyFromPrivate(privKeyHex);
  const signature = keys.sign(hashed_data, { canonical: true });
  const sig = signature.toDER('hex');
  console.log("Signature:", sig);
  return sig
}


    
async function react(item, iden, code=null, button=null){
  console.log('react', code)
  
  userData = get_stored_userData();
  // // console.log(storedData)
  // var userData = storedData[0];
  // var userArrayData = storedData[1];

  if (item == 'verify') {
    modalPopUp('Verify Me', '/utils/verify_post_modal/' + iden)
    return
  } else if (item == 'modelData') {
    modalPopUp('Model Data', '/utils/generic_modal_data/modelData/' + iden)
    return
  } else if (item == 'insight') {
    modalPopUp('Insights', '/utils/post_insight_modal/' + iden)
    return
  } else if (item == 'more') {
    modalPopUp('More Options', '/utils/post_more_options_modal/' + iden)
    return
  } else if (item == 'share') {

  } else if (userData == null || userData == 'null') {
    modalPopUp('Login / Signup', '/accounts/login-signup')
  } else {
    if(item == 'follow2'){
      // alert(iden)
      var navBar = document.getElementById('navBar');
      // alert(navBar)
      follow = item.split('-')[0]
      // console.log(follow)
      li = navBar.getElementsByClassName('follow')[0]
      // alert(li)
      // SpeechRecognitionAlternative(li)
      li.classList.toggle('active');
      // alert(iden)
      if (iden.includes('?follow=')||iden.includes('&follow=')){
        link = iden
      } else {
        link = '?follow=' + iden
      }
      // console.log(link)
      $.get(link, function(data){
        // console.log('receveid dreturn data')
        // console.log(data)
        // console.log(data.replace(/&quot;|&#039;/g, '"'))
        // if (data.includes('Login')){
        //   alert('Please Login')
        // }
          var parser = new DOMParser();
          var htmlDoc = parser.parseFromString(data, 'text/html');
        // ParsedElements = $.parseHTML(data)
        // console.log(htmlDoc)
        check_instructions(htmlDoc)
      });
    // } else if (item == 'saveButton') {
    //   button = 'saveButton' + '-' + item
    //   li = document.getElementsByClassName(button)[0]
    //   li.innerHTML = 'Saved'

    } else {
      const data = {'item':item, 'post_id':iden}
      var rs = document.getElementsByClassName('reactionBar');
      var convert_to_none = false;
      for(i=0; i<rs.length; i++){
        if (rs[i].id == iden){
          if (item == 'yea'){
            // alert('yea')
            li = rs[i].getElementsByClassName('yea')[0]
            if(String(li.classList).includes('active')){
              convert_to_none = true
            } 
            li.classList.toggle('active');
            li.classList.add('depress');
            // alert(li.classList)
            li2 = rs[i].getElementsByClassName('nay')[0]
            li2.classList.remove('active');
            // li.focus()
            // alert(li.classList)
          }else if (item == 'nay'){
            li = rs[i].getElementsByClassName('nay')[0]
            if(String(li.classList).includes('active')){
              convert_to_none = true
            }
            li.classList.toggle('active');
            li.classList.add('depress');
            li2 = rs[i].getElementsByClassName('yea')[0]
            li2.classList.remove('active');
          
          } else if (item == 'follow' || item == 'unfollow') {
            console.log('is follow')
            var post_id = iden
          //   // var userData = localStorage.getItem("userData");
          //   storedData = get_stored_userData();
            console.log(userData.follow_post_id_array)
          //   var userData = storedData[0];
          //   var userArrayData = storedData[1];
          //   // // userData = JSON.parse(userData)
            // if (item == 'follow') {
            //   if (userArrayData.follow_post_id_array.length > 980) {
            //     userArrayData.follow_post_id_array.shift()
            //   }
            //   userArrayData.follow_post_id_array.push(post_id);
            // } else if (item == 'unfollow') {
            //   // var follow_post_id_array = JSON.parse(userData.follow_post_id_array.replace(/'/g, '"'));
            //   var index = userArrayData.follow_post_id_array.indexOf(post_id);
            //       if (index !== -1) { 
            //         userArrayData.follow_post_id_array.splice(index, 1);
            //       }
            // }

          //   // localStorage.setItem('userData', JSON.stringify(data));
          //   // var userData = localStorage.getItem("userData");
          //   console.log(JSON.stringify(userData))
          //   console.log(JSON.stringify(userArrayData))
          //   // userData = JSON.parse(userData)
          //   console.log('2')
          //   // console.log(JSON.stringify(userData.interest_array))
          //   // var interest_array = JSON.parse(JSON.stringify(userData.interest_array).replace(/'/g, '"'));
          //   // // console.log(interest_array)
          //   // var follow_topic_array = JSON.parse(JSON.stringify(userData.follow_topic_array).replace(/'/g, '"'));
          //   // userData.interest_array = interest_array
          //   // userData.follow_topic_array = follow_topic_array
            
          //   // var follow_post_id_array = JSON.parse(JSON.stringify(userData.follow_post_id_array).replace(/'/g, '"'));
          //   // follow_post_id_array.push(cmd.post_id);
          //   // userData.follow_post_id_array = follow_post_id_array
          //   // console.log(JSON.stringify(userData))
          //   // console.log('---')
        
          //   // console.log(userArrayData.interest_array)
          //   // var interest_array = JSON.parse(userData.interest_array.replace(/'/g, '"'));
          //   // console.log(interest_array)
          //   // console.log('3')
          //   // var follow_topic_array = JSON.parse(userData.follow_topic_array.replace(/'/g, '"'));
          //   userData.interest_array = userArrayData.interest_array
          //   userData.follow_topic_array = userArrayData.follow_topic_array
            
          //   var follow_post_id_array = JSON.parse(userData.follow_post_id_array.replace(/'/g, '"'));
          //   // follow_post_id_array.push(post_id);
          //   var index = follow_post_id_array.indexOf(post_id);
          //       if (index !== -1) { 
          //         follow_post_id_array.splice(index, 1);
          //       }
          //   userData.follow_post_id_array = follow_post_id_array
          //   console.log(JSON.stringify(userData))
          // //   console.log('---')
          // storedData = get_stored_userData();
          // // // console.log(storedData)
          // var userData = storedData[0];
          // var userArrayData = storedData[1];
          // var userData = localStorage.getItem("userData");
          // // console.log(userData)
          // // userData = JSON.parse(userData)
          // var userArrayData = {}
          // userArrayData.interest_array = JSON.parse(JSON.stringify(userData.interest_array).replace(/'/g, '"'))
          // userArrayData.follow_topic_array = JSON.parse(JSON.stringify(userData.follow_topic_array).replace(/'/g, '"'));
          // userArrayData.follow_post_id_array = JSON.parse(JSON.stringify(userData.follow_post_id_array).replace(/'/g, '"'));
          // console.log('2')
          // console.log(JSON.stringify(userData.interest_array))
          // var interest_array = x;
          // console.log(interest_array)
          // var 
          // interest_array = JSON.parse(interest_array)
          try{
            follow_post_id_array = JSON.parse(userData.follow_post_id_array)
          } catch(err) {
            follow_post_id_array = userData.follow_post_id_array
          }
          if (item == 'follow') {
            if (follow_post_id_array.length > 980) {
              follow_post_id_array.shift()
            }
            follow_post_id_array.push(post_id);
          } else if (item == 'unfollow') {
            // var follow_post_id_array = JSON.parse(userData.follow_post_id_array.replace(/'/g, '"'));
            var index = follow_post_id_array.indexOf(post_id);
                if (index !== -1) { 
                  follow_post_id_array.splice(index, 1);
                }
          }
          userData.follow_post_id_array = JSON.stringify(follow_post_id_array)
          // var follow_post_id_array = 
          // userArrayData.follow_post_id_array.push(cmd.post_id);
          // var index = follow_post_id_array.indexOf(cmd.post_id);
          // // console.log('index', index)
          // if (index !== -1) { 
          //   follow_post_id_array.splice(index, 1);
          // }
          // userData.follow_post_id_array = userArrayData.follow_post_id_array
          console.log(JSON.stringify(userData))
          console.log('---')
        

          //   console.log('show button press', item)
            li = rs[i].getElementsByClassName('follow')[0]
            li.classList.toggle('active');
            li.classList.add('depress');
          //   userData = await sign(userData)
          userData = await sign_userData(userData)
          return_signed_userData(userData)
          //   // sign_and_return_userData(userData, userArrayData);


          //   const postData = {};
          //   postData['objData'] = JSON.stringify(userData);
          //   // postData['localData'] = JSON.stringify(userData);
          //   // console.log('postData',postData)
          //   // console.log('send to receive_interaction_data')
            
          //   $.ajax({
          //     type:'POST',
          //     // url:'/accounts/receive_test_data',
          //     url:'/accounts/receive_interaction_data',
          //     data: postData,
          //     success:function(response){
          //       console.log(response)
          //     }
          //   });

            
          } else {
            li = rs[i].getElementsByClassName(item)[0]
            li.classList.toggle('active');
            li.classList.add('depress');
            // alert('done')
          }
        }

      }
      try {
        setTimeout(function (){
          // alert(li.classList)
          li.classList.remove('depress');     
          // alert(li.classList)
  
        }, 200);
      } catch(err) {console.log(err)}
      // alert('n')
      if (convert_to_none){
        item = 'None'
      }
      if (item != 'share' && item != 'follow' && item != 'unfollow') {
        console.log('makerequest for interaction object')
        // console.log(data)
        makeAjaxRequest({}, '/accounts/reaction/' + iden + '/' + item, data)
          .then(signReturnInteraction)
          .catch(error => {
            console.error('There was a problem with the AJAX request:', error);
        });


        
        // $.get('/accounts/reaction/' + iden + '/' + item, function(data){
        //   // return JsonResponse({'message' : 'Please fill, sign and return', 'data' : get_signing_data(vote)})

        //   // alert(data)
        //   if (data.includes('Login')){
        //     alert('Please Login')
        //   } else if (item == 'follow'){
        //     alert(data)
        //   }

        // });
      }
    }
  }

  
}
async function signReturnInteraction({ response, item }) {
  // console.log('receive signReturnInteraction data')
  // console.log(response);
  data = JSON.parse(response['data']);
  // console.log(data['object_type'])
  // console.log(item)
  cmd = item
  userData = get_stored_userData()
  user_id = userData.id
  data.User_obj = user_id
  if (data['object_type'] == 'UserVote') {
    if (data.voteValue == 'yea' && cmd.item == 'yea' || data.voteValue == 'nay' && cmd.item == 'nay') {
      data.voteValue = 'none'
    } else {
      data.voteValue = cmd.item
    }
    
  } else if (data['object_type'] == 'SavePost') {
    if (data.saved == false) {
      data.saved = true
      post_save_state = true
    } else {
      data.saved = false
      post_save_state = false
    }
  }



  data = await sign_data(data)
  // userData = await sign(userData)
  // console.log(JSON.stringify(userData))
  const postData = {};
  postData['objData'] = JSON.stringify(data);
  console.log('---')
  // console.log(postData)
  $.ajax({
    type:'POST',
    // url:'/accounts/receive_test_data',
    url:'/accounts/receive_interaction_data',
    data: postData,
    success:function(response){
      console.log(response)
      if (response['message'] == 'Success') {
        if (item.item == 'saveButton') {
          li = document.getElementsByClassName('saveButton, clickable')[0]
          if (post_save_state == true) {
            li.innerHTML = 'Saved'
          } else {
            li.innerHTML = 'Save'
          }
        }
      //     field3.innerHTML = 'Username does not match password'
      // } else if (response['message'] == 'Valid Username and Password'||response['message'] == 'User Created') {
      //   console.log('proceed to login')
      //   // console.log(JSON.stringify(response['userData']))
      //   localStorage.setItem('passPrivKey', keyPair[0]);
      //   localStorage.setItem('passPubKey', keyPair[1]);
      //   localStorage.setItem('display_name', JSON.parse(response['userData'])['display_name']);
      //   localStorage.setItem('userData', response['userData']);
      //   login()
      //   // modalPopUp('Select Region', '/accounts/get_country_modal')
      } else {
        console.log('else, post-interaction')
        if (data['object_type'] == 'UserVote') {
          // data.vote = item
          if (item == 'yea'){
            // alert('yea')
            li = rs[i].getElementsByClassName('yea')[0]
            // if(String(li.classList).includes('active')){
            //   convert_to_none = true
            // } 
            li.classList.toggle('active');
            li.classList.add('depress');
            // alert(li.classList)
            // li2 = rs[i].getElementsByClassName('nay')[0]
            // li2.classList.remove('active');
            // li.focus()
            // alert(li.classList)
          }else if (item == 'nay'){
            li = rs[i].getElementsByClassName('nay')[0]
            // if(String(li.classList).includes('active')){
            //   convert_to_none = true
            // }
            li.classList.toggle('active');
            li.classList.add('depress');
            // li2 = rs[i].getElementsByClassName('yea')[0]
            // li2.classList.remove('active');
          }

        }
        alert(response['message'])
      }
    },
    error: function (xhr, ajaxOptions, thrownError) {
      console.log('prob2')
      field3.innerHTML = 'Failed to reach server';
    } 
  });
      
}

// function myFunction(iden) {
//   // Get the text field
//   var copyText = document.getElementById(iden);
//   alert(copyText)
//   // Select the text field
//   copyText.select();
//   copyText.setSelectionRange(0, 99999); // For mobile devices

//   // Copy the text inside the text field
//   navigator.clipboard.writeText(copyText.value);
  
//   // Alert the copied text
//   alert("Copied the text: " + copyText.value);
// }
// const copyToClipboard = async (iden) => {
//   alert(iden)
//   // let a = document.getElementsByClassName(iden);
//   // alert(a)
//   // alert(a.id)
//   // let text = 'testcopy'
//   // var copyText = document.getElementById(iden);
//   // alert(copyText)
//   try{
//     /* Get the text field */
//     var copyText = 'testcopy'
      
//      /* Copy the text inside the text field */
//     navigator.clipboard.writeText(copyText);
  
//     /* Alert the copied text */
//     alert("Copied: " + copyText);
//   }catch(err){alert(err)}
// }

function mobileShare(iden, code=null) {
  // var rs = document.getElementsByClassName('reactionBar');
  // for (i=0;i<rs.length;i++) {
  //   if (rs[i].id == iden) {
  //     li = rs[i].getElementsByClassName('share')[0]
  //     li.classList.toggle('active');
  //     li.classList.add('depress');
  //   }
  // }
  modalPopUp('Share Post', '/utils/share_modal/' + iden)
    $.get('/utils/mobile_share/' + iden, function(data){
      setTimeout(function (){
        li.classList.remove('active');     
        li.classList.remove('depress'); 
      }, 200);
    });

}

function copyToClipboard(text) {
  if (text[0] == '/') {
    text = 'SoVote.center' + text
    // alert(text)
  }
  try{
    navigator.clipboard.writeText(text).then(() => {
      alert("copied " + text);
    });
  }catch(err){}

}

function readAloud(iden){
  // alert('start')
  card = document.getElementById(iden);
  let text = $(card).find('.TextContent').text()
  let control = $(card).find('.listen').text()
  var msg = new SpeechSynthesisUtterance(text);
  // alert(control)
  if(control == 'Read Aloud'){
    $(card).find('.listen').text('Pause Player')
    window.speechSynthesis.cancel(msg);
    window.speechSynthesis.speak(msg);
    // alert(window.speechSynthesis.speaking);
    // alert('done')
  }else if (control == 'Pause Player'){
    $(card).find('.listen').text('Resume Player')
    window.speechSynthesis.cancel(msg);
  }else if (control == 'Resume Player'){
    $(card).find('.listen').text('Pause Player')
    window.speechSynthesis.resume(msg);
  } 
}
function removeNotification(iden){
  
  $.get('/utils/remove_notification/' + iden, function(data){});
  n = document.getElementsByClassName('notification')
  for(i=0;i<n.length;i++){
    if(n[i].id == iden){
      // alert('remove')
      n[i].remove()
      // alert('removed')
    }
  }
}
function addNotification(word){
  // alert(word);
  $.get('/utils/test_notification', function(data){});
}
function calendarWidget(){
  c = document.getElementById('calendarForm');
  c.classList.toggle('showForm');
}
// function datePickerWidget(){
//   c = document.getElementById('datePickerForm');
//   c.classList.toggle('showForm');
// }
function subNavWidget(value){
  console.log('value:', value)
  function activate(element, show, delay) {
    // console.log(element, show, delay)
    if (show) {
      element.classList.add('active');
      // setTimeout(function() {
      //     element.classList.add('active');
      // }, 500);
    } else {
      if (delay) {
        setTimeout(function() {
            element.classList.remove('active');
        }, 200);
      } else {
        element.classList.remove('active');
      }
    }
  }

  navBar = document.getElementById('navBar')
  ul = navBar.getElementsByTagName('ul')[0]
  ul.classList.toggle('bottomBorder')
  li = navBar.getElementsByTagName('li')
  for(i=0;i<li.length;i++){
    if (li[i].classList.contains(value) || li[i].textContent.includes('Current') || li[i].textContent.includes('Upcoming')){
      if (li[i].classList.contains('active')) {
        activate(li[i], false, true)
      } else {
        activate(li[i], true, true)
      }
    } else {
      if (li[i].classList.contains('active')) { }
        activate(li[i], false, false)
    }
  }
  function activate_menu(element, show) {
    if (show) {
      element.classList.add('showFormA');
      setTimeout(function() {
          element.classList.add('showForm');
      }, 10);
    } else {
      element.classList.remove('showForm');
      setTimeout(function() {
          element.classList.remove('showFormA');
      }, 200);
    }
  }
  navOptions = document.getElementById('navOptions')
  subNavs = navOptions.getElementsByTagName('div')
  for(i=0;i<subNavs.length;i++){
    try{
      if (value == subNavs[i].id){
        if (subNavs[i].classList.contains('showForm')) {
          activate_menu(subNavs[i], false)
        } else {
          activate_menu(subNavs[i], true)
        }
      } else {
        if (subNavs[i].classList.contains('showForm')) {
          activate_menu(subNavs[i], false)
        }
      }
    }catch(err){
      // console.log(err)
    }
  }
}
function sidebarSort_old(head){
  // alert(head)
  if(head.includes('-')){
    var title = head.split('-')[0];
    var task = head.split('-')[1];
    var list = document.getElementById(title).nextElementSibling.firstElementChild;
    var items = list.childNodes;
    var itemsArr = [];
    for (var i in items) {
        if (items[i].nodeType == 1) { // get rid of the whitespace text nodes
          itemsArr.push(items[i]);
        }
    }
    if(task == 'inst'){
      // alert('inst')
      a = document.getElementById(title);
      var b = title + '-alpha'
      $(a).children().first().remove()
      code = `<span onclick="sidebarSort('` + b + `')">sort</span>`
      $(a).append(code) 
      // alert(parseInt(itemsArr[0].firstElementChild.firstElementChild.innerHTML.replace('(', '').replace(')','')))
      // alert(b.innerHTML)
      itemsArr.sort(function(a, b) {
        return a.innerHTML == b.innerHTML
                ? 0
                : (parseInt(b.firstElementChild.firstElementChild.innerHTML.replace('(', '').replace(')','')) > parseInt(a.firstElementChild.firstElementChild.innerHTML.replace('(', '').replace(')','')) ? 1 : -1);
      });
    }else{
      // alert('alpha')
      a = document.getElementById(title);
      var b = title + '-inst'
      $(a).children().first().remove()
      code = `<span onclick="sidebarSort('` + b + `')">sort</span>`
      $(a).append(code) 
      itemsArr.sort(function(a, b) {
        return a.innerHTML == b.innerHTML
                ? 0
                : (a.innerHTML > b.innerHTML ? 1 : -1);
      });
    }
    for (i = 0; i < itemsArr.length; ++i) {
      list.appendChild(itemsArr[i]);
    }
  }else{
    // clear notifications
  }

}

function sidebarSort(head){
  // alert(head)
  var isMobile = document.getElementById('isMobile').name;

  if(head.includes('-')){
    var title = head.split('-')[0];
    var task = head.split('-')[1];
    if (isMobile == 'True'){
      var pages = document.getElementsByClassName('searchTabContent show block')[0];
      var list = pages.firstElementChild.nextElementSibling;
      a = pages;
      var items = list.childNodes;
      var itemsArr = [];
      for (var i in items) {
          if (items[i].nodeType == 1) { // get rid of the whitespace text nodes
            itemsArr.push(items[i]);
          }
      }
      if(task == 'inst'){
        var b = title + '-alpha'
       $(a).children().first().remove()
       $(a).children().eq(1).remove()
        code = `<div><span class="sort" onclick="sidebarSort('` + b + `')">sort</span></div>`
        itemsArr.sort(function(a, b) {
          return a.innerHTML == b.innerHTML
                  ? 0
                : (parseInt(b.firstElementChild.firstElementChild.innerHTML.replace('(', '').replace(')','')) > parseInt(a.firstElementChild.firstElementChild.innerHTML.replace('(', '').replace(')','')) ? 1 : -1);
        });
      }else{
        var b = title + '-inst'
        $(a).children().first().remove()
        $(a).children().eq(1).remove()
        code = `<div><span class="sort" onclick="sidebarSort('` + b + `')">sort</span></div>`
        itemsArr.sort(function(a, b) {
          return a.innerHTML == b.innerHTML
                  ? 0
                  : (a.firstElementChild.innerHTML > b.firstElementChild.innerHTML ? 1 : -1);
        });
      }
      for (i = 0; i < itemsArr.length; ++i) {
        list.appendChild(itemsArr[i]);
      }
      $(a).prepend(code) 
    } else {
      var list = document.getElementById(title).nextElementSibling.firstElementChild;
      var items = list.childNodes;
      var itemsArr = [];
      for (var i in items) {
          if (items[i].nodeType == 1) {
            itemsArr.push(items[i]);
          }
      }
      if(task == 'inst'){
      a = document.getElementById(title);
      var b = title + '-alpha'
        $(a).children().first().next().remove()
        code = `<span class="sort" onclick="sidebarSort('` + b + `')">sort</span>`
        $(a).append(code) 
        itemsArr.sort(function(a, b) {
          return a.innerHTML == b.innerHTML
                  ? 0
                  : (parseInt(b.firstElementChild.firstElementChild.innerHTML.replace('(', '').replace(')','')) > parseInt(a.firstElementChild.firstElementChild.innerHTML.replace('(', '').replace(')','')) ? 1 : -1);
        });
      }else{
        a = document.getElementById(title);
        var b = title + '-inst'
        $(a).children().first().next().remove()
        code = `<span class="sort" onclick="sidebarSort('` + b + `')">sort</span>`
        $(a).append(code) 
        itemsArr.sort(function(x, y) {
          return x.innerHTML == y.innerHTML
                  ? 0
                  : (x.firstElementChild.innerHTML > y.firstElementChild.innerHTML ? 1 : -1);
        });
      }
      for (i = 0; i < itemsArr.length; ++i) {
        list.appendChild(itemsArr[i]);
      }
    }
    
    
  }else{
    // clear notifications
  }

}



function insertEmbed(iden, link){
  var card = document.getElementById(iden);
  var word = $(card).find('.watch').text() 
  if (word == 'Watch'){
    code = '<iframe class="EmbedContent" src="' + link + '" allowfullscreen></iframe>'
    // alert(link)
    $(card).find('.Embed').prepend(code)  
    // alert('1')
    $(card).find('.watch').text('Close Player')
    // alert('2')

  }else{
    $(card).find('.Embed').empty()
    $(card).find('.watch').text('Watch')

  }
}

function tocNav(item){
  console.log('tocNav',item)
  var hs = document.getElementsByTagName('h2')
  for(i=0; i<hs.length; i++){
    if(hs[i].outerHTML.includes(item)){
      scrollToElement(hs[i], 10, true)
      // .scrollIntoView({ behavior: 'smooth', block: 'start' });
      break
    }
  }
  item = item.replaceAll("'", '"')
  var hs = document.querySelectorAll("[style*='text-align:Center']")
  for(i=0; i<hs.length; i++){
    if(hs[i].outerHTML.includes(item)){
      scrollToElement(hs[i], 10, true)
      // hs[i].scrollIntoView({ behavior: 'smooth', block: 'start' });
      break
    }
  }
  function searchelement(elementhtml){
    try{
      [...document.querySelectorAll("*")].forEach((ele)=>{
        if(ele.outerHTML == elementhtml){
          scrollToElement(ele, 10, true)
          // ele.scrollIntoView({ behavior: 'smooth', block: 'start' });
          // break
        }
      });

    }catch(err){console.log(err)}

   }
  searchelement(item)
  var isMobile = document.getElementById('isMobile').name;
  if (isMobile == 'True'){
    mobileSwitch('search')

  }
}
function continue_reading(iden, direction){
  // alert('start')
  console.log('continue reading', iden)
  var card = document.getElementById(iden);
    if (direction == 'more'){
      // alert('more')
      try{
        // $(card).find('.hansardText').attr("style","max-height:none");
        // $(card).find('.hansardTextContent').attr("style","max-height:none");
        $(card).find('.Text').addClass('showFullText');
        $(card).find('.TextContent').addClass('showFullText');
        $(card).find('.fadeOut').remove()
        $(card).find('.TextContent').next().text("Read Less")
        $(card).find('.TextContent').next().attr("onclick","continue_reading('" + iden + "', 'less')");
        // alert('done')
      }catch(err){}
      // try{
      //   // alert('1')
      //   // $(card).find('.billSummary').attr("style","max-height:none");
      //   $(card).find('.billSummary').addClass('showFullText');
      //   $(card).find('.fadeOut').remove()
      //   // alert('2')
      //   // alert( $(card).find('.billSummary').next())
      //   $(card).find('.Details').next().text("Read Less")
      //   $(card).find('.Details').next().attr("onclick","continue_reading('" + iden + "', 'less')");
      //   // alert('done')
      // }catch(err){alert(err)}

    }else if (direction == 'less'){
      try{
        // $(card).find('.hansardText').attr("style","max-height:150px");
        // $(card).find('.hansardTextContent').attr("style","max-height:150px");
        $(card).find('.Text').removeClass('showFullText');
        $(card).find('.TextContent').removeClass('showFullText');
        $(card).find('.TextContent').next().text("Read More")
        $(card).find('.TextContent').next().attr("onclick","continue_reading('" + iden + "', 'more')");
        var text = card.getElementsByClassName('TextContent')[0];
        fade = "<div class='fadeOut'></div>"
        $(text).append(fade) 
        scrollToElement(card)
        // card.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }catch(err){}
      // try{
      //   // $(card).find('.billSummary').attr("style","max-height:150px");
      //   $(card).find('.billSummary').toggleClass('showFullText');
      //   $(card).find('.Details').next().text("Read More")
      //   $(card).find('.Details').next().attr("onclick","continue_reading('" + iden + "', 'more')");
      //   var text = card.getElementsByClassName('billSummary')[0];
      //   fade = "<div class='fadeOut'></div>"
      //   $(text).append(fade) 
      //   card.scrollIntoView({ behavior: 'smooth', block: 'start' });
      // }catch(err){}
    }else{
      $.get('/utils/continue_reading/' + iden + '/?topic=' + direction, function(data){
        $(card).find('.Terms').text("")
        $(card).find('.Terms').append(data)
        $(card).find('.Terms').next().text("")
        $(card).find('.readMoreTerms').text("")
      });

    }
  // }
}
function show_all(iden, item){
  // alert(item)
  try{
      var subscribers = document.getElementsByClassName('showAllCentered');
      for(i=0; i<subscribers.length; i++){
          subscribers[i].outerHTML = "";
      }
  }catch(err){alert(err)}
  if(item != 'function close() { [native code] }'){
      $.get('/utils/show_all/' + iden + '/' + item, function(data) {
          // alert(data)
          if(item == 'terms'){
            title = 'All Topics'
          }else{
            title = "All Speakers"
          }
          code = '<div class="showAllCentered"><div id="showAllClose" onclick="show_all(100, close)">Close</div><div id="title">' + title + '</div>' + data  + '</div>'
          $('#container').prepend(code)
      });
  }
};
function login() {
  // var username = localStorage.getItem("username");
  // var dom = document.getElementById('userName');
  // dom.innerHTML = "<a href='/user/" + username + "'><span style='color:#b78e12'>V</span><span style='color:gray'>/</span>" + username + "</a>"
  // var settingsLink = document.getElementById('settingsLink')
  // settingsLink.innerHTML = "<a href='/user/settings'>Settings</a>"
  // var logoutLink = document.getElementById('logoutLink')
  // logoutLink.innerHTML = "<span style='cursor:pointer' onclick='logout()'>Log Out</span>"
  index = document.getElementById('navigation');
  index.innerHTML = '<div class="lds-dual-ring"></div>';
  closeModal();
  $.ajax({
    // type:'POST',
    url:'/accounts/get_index',
    // data: data,
    success:function(response){
      // console.log('received response')
      // index = document.getElementById('index');
      // index.outerHTML = response;
      location.reload()
      // console.log('done')
    },
    // error: function (xhr, ajaxOptions, thrownError) {
    //   field3.innerHTML = 'Failed to reach server';
    // } 
  });
}
async function logout(target) {
  console.log('logout',target)
  // console.log(target)
  // userData, userArrayData = get_stored_userData()
  // console.log(userData.must_rename)
      
  const resp = await connect_to_node(target);
  console.log('modal response:', resp);
  if (resp) {
    // maybe use this:
    // indexedDB.deleteDatabase('KeyDB');

      await storeItem(null, 'PrivKey');
      await storeItem(null, 'PubKey');
      await storeItem(null, 'username');
      await storeItem(null, 'userData');
      await storeItem(null, 'password');
      await storeItem(null, 'display_name');
      await storeItem(null, 'user_id');
      location.reload()

  } else {
    alert('Failed to reach server');
  }
  // $.ajax({
  //   url: target,
  //   success: async function (data) {
  //     await storeItem(null, 'PrivKey');
  //     await storeItem(null, 'PubKey');
  //     await storeItem(null, 'username');
  //     await storeItem(null, 'userData');
  //     await storeItem(null, 'password');
  //     await storeItem(null, 'display_name');
  //     await storeItem(null, 'user_id');
  //     // localStorage.setItem('bioPrivKey', null);
  //     // localStorage.setItem('bioPubKey', null);
  //     // localStorage.setItem('passPrivKey', null);
  //     // localStorage.setItem('passPubKey', null);
  //     // localStorage.setItem('username', null);
  //     // localStorage.setItem('userData', null);
  //     // localStorage.setItem('pass', null);
  //     // localStorage.setItem('display_name', null);
  //     // localStorage.setItem('user_id', null);
  //     // localStorage.setItem('userData', null);
  //     location.reload()
  //     // index = document.getElementById('index');
  //     // index.outerHTML = data;
  //     // console.log('logout2')
  //     // var dom = document.getElementById('userName');
  //     // console.log(dom)
  //     // dom.innerHTML = `<span onclick="modalPopUp('Authenticate', '/accounts/authenticate')">Authenticate</span>`;
      
  //     // console.log('logout3')
  //     // var settingsLink = document.getElementById('settingsLink')
  //     // settingsLink.innerHTML = ""
  //     // console.log('logout4')
  //     // var logoutLink = document.getElementById('logoutLink')
  //     // logoutLink.innerHTML = ""
  //   },
  //   error: function (xhr, ajaxOptions, thrownError) {
  //     alert('Failed to reach server');
  //   } 
  // });
}
async function clearLocalUserData(pass) {
  console.log('clearLocalUserData')
  console.log(pass)
  // console.log(JSON.parse(pass))
  if (pass == await getItem("password")) {
    await storeItem(null, 'PrivKey');
    await storeItem(null, 'PubKey');
    await storeItem(null, 'username');
    await storeItem(null, 'userData');
    await storeItem(null, 'password');
    await storeItem(null, 'display_name');
    await storeItem(null, 'user_id');

    // localStorage.setItem('bioPrivKey', null);
    // localStorage.setItem('bioPubKey', null);
    // localStorage.setItem('passPrivKey', null);
    // localStorage.setItem('passPubKey', null);
    // localStorage.setItem('username', null);
    // localStorage.setItem('userData', null);
    // localStorage.setItem('pass', null);
    // localStorage.setItem('display_name', null);
    var field4 = document.getElementById('field4');
    field4.innerHTML = 'Cleared';
  }
  

}
function generatePassword() {
  // // var length = 20,
  // //     charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%&",
  // //     retVal = "";
  // // for (var i = 0, n = charset.length; i < length; ++i) {
  // //     retVal += charset.charAt(Math.floor(Math.random() * n));
  // // }
  // var length = 32;
  // const uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  //   const lowercase = 'abcdefghijklmnopqrstuvwxyz';
  //   const numbers = '0123456789';
  //   const specialCharacters = '!@#$%^&*()-_=+[]{}|;:,.<>?';

  //   // Combine all characters into a single string
  //   const allCharacters = uppercase + lowercase + numbers + specialCharacters;

  //   let password = '';

  //   // Ensure at least one character from each group is in the password
  //   password += uppercase[Math.floor(Math.random() * uppercase.length)];
  //   password += lowercase[Math.floor(Math.random() * lowercase.length)];
  //   password += numbers[Math.floor(Math.random() * numbers.length)];
  //   password += specialCharacters[Math.floor(Math.random() * specialCharacters.length)];

  //   // Fill the rest of the password length with random characters
  //   for (let i = password.length; i < length; i++) {
  //       password += allCharacters[Math.floor(Math.random() * allCharacters.length)];
  //   }

  //   // Shuffle the password to ensure the first four characters aren't predictable
  //   password = password.split('').sort(() => Math.random() - 0.5).join('');
  //   console.log(password)
  //   // return password;
  
  const strength = 256; // 24-word mnemonic
  const password = generateMnemonic(wordlist, strength);
  console.log("Mnemonic (24 words):", mnemonic);

  var form = document.getElementById("modalForm");
  form.elements["password"].value = password;
}
function displayPassword() {
    var clicker = document.getElementById("showPassword");
    
    if (clicker.innerHTML == 'Show Passphrase') {
        clicker.innerHTML = ' Hide Passphrase '
        var x = document.getElementById("password");
        x.type = "text";
    } else {
        clicker.innerHTML = 'Show Passphrase'
        var x = document.getElementById("password");
        x.type = "password";

    // if (clicker.innerHTML == 'visibility_off') {
    //     clicker.innerHTML = 'visibility'
    //     var x = document.getElementById("password");
    //     x.type = "text";
    // } else {
    //     clicker.innerHTML = 'visibility_off'
    //     var x = document.getElementById("password");
    //     x.type = "password";

    }
}
function modalPopPointer(value){
  console.log(value)
  items = value.split(', ')
  console.log(items)
  modalPopUp(items[0].replace(/"/g, ''), items[1].replace(/"/g, ''))
}
async function modalPopUp(title, target){
  // console.log('popup',target)
  // closeModal()
  var isMobile = document.getElementById('isMobile').name;
  console.log('ismobile:',isMobile);
  // if (isMobile == 'True') {
  // }
  document.querySelector('.darkenOverlay').classList.add('darken');
  m = document.getElementsByClassName('modalWidget')[0]
  modal = $('.modalWidget');
  // if (modal.hasClass('show')) {
  //   modal.removeClass('show');
  // }
  if (target != null) {
    code = '<div class="lds-dual-ring"></div>'
    m.querySelector("#modalContent").innerHTML = code;
  }
  
  m.querySelector("#modalTitle").innerHTML = title;
  modal.addClass('show');
  setTimeout(function() {
    modal.addClass('fade-in');
}, 10);

  // modal.addClass('fade-in');
  // m.addEventListener('transitionend', () => {
  //   console.log('compl')
  // });
  
  if (target != null) {
    if (target.includes('/')) {
      target = target
    } else {
      target = '/utils/default_modal/' + target
    }
    try {
      userData = JSON.parse(await getItem('userData'))
      target = target + '?userId=' + userData['id']
    } catch(err) {}
    // console.log(target)
    
    const data = await connect_to_node(target);
    // console.log('modal response:', data);
    if (data) {
      console.log('data received')
        var html = $('<html>').html(data);
        var new_title = html.find('title').text();
        m.querySelector("#modalTitle").innerHTML = new_title;
        var instruction = html.find('#instruction').attr('value');
        m.querySelector("#modalContent").innerHTML = data;
        enact_user_instruction(instruction, {})
        console.log('addEventListener')
    const usernameInput = document.getElementById("username");
    const statusSpan = document.getElementById("username-status");
    if (!usernameInput || !statusSpan) return;

    let timeout = null;

    usernameInput.addEventListener("input", function () {
        clearTimeout(timeout);
        const username = usernameInput.value;

        if (!username.trim()) {
            statusSpan.textContent = "";
            return;
        }

        timeout = setTimeout(() => {
            fetch(`/accounts/username_avail/?username=${encodeURIComponent(username)}`)
                .then(response => response.json())
                .then(data => {
                    if (data.available) {
                        // statusSpan.textContent = " ✓";
                        statusSpan.textContent = "Available";
                        statusSpan.style.color = "green";
                    } else {
                        // statusSpan.textContent = " ✗";
                        statusSpan.textContent = "Not Available";
                        statusSpan.style.color = "red";
                    }
                })
                .catch(error => {
                    statusSpan.textContent = "Error";
                    statusSpan.style.color = "gray";
                });
        }, 300);
    });

    } else {
      m.querySelector("#modalContent").innerHTML = 'Failed to reach server';
    }
    // $.ajax({
    //   url: target,
    //   success: function (data) {
        // var head = document.getElementsByTagName('head')[0],
        //     script = document.createElement('script');
        // script.src = 'https://unpkg.com/@simplewebauthn/browser@9.0.1/dist/bundle/index.umd.min.js';
        // head.appendChild(script);
        // parsedData = $.parseHTML(data);
        // var new_cards =  $(parsedData);
    //     var html = $('<html>').html(data);
    //     var new_title = html.find('title').text();
    //     m.querySelector("#modalTitle").innerHTML = new_title;
    //     var instruction = html.find('#instruction').attr('value');
    //     m.querySelector("#modalContent").innerHTML = data;
    //     enact_user_instruction(instruction, {})
    //   },
    //   error: function (xhr, ajaxOptions, thrownError) {
    //     m.querySelector("#modalContent").innerHTML = 'Failed to reach server';
    //   } 
    // });
  }
  
}

function closeModal(){
  // console.log('close modal')
  m = document.getElementsByClassName('modalWidget')[0]
  modal = $('.modalWidget');
  modal.removeClass('fade-in');
  modal.addClass('fade-out');
  var isMobile = document.getElementById('isMobile').name;
  if (isMobile == 'True') {
    modal.removeClass('show');
    modal.removeClass('fade-out');
    document.querySelector('.darkenOverlay').classList.remove('darken');
  } else {
    document.querySelector('.darkenOverlay').classList.remove('darken');
    function handleTransition(event) {
      modal.removeClass('show');
      modal.removeClass('fade-out');
      m.removeEventListener('transitionend', handleTransition);
    }
    m.addEventListener('transitionend', handleTransition);
  }
}
function removeModalClose(){
  btn = document.getElementsByClassName('modalWidgetClose')[0]
  btn.setAttribute('onclick','')
  btn.innerHTML = '-'
}
function onFormSubmit() {
  event.preventDefault();
}
function encryptMessage(publicKey, keyPair, message) {
      console.log('encrypt_message')
      const curve = new elliptic.ec('secp256k1');
  const recipientKey = curve.keyFromPublic(publicKey, 'hex');
  const sharedSecret = keyPair.derive(recipientKey.getPublic());
  const sharedKey = CryptoJS.enc.Hex.parse(sharedSecret.toString(16).slice(0, 32));

  const iv = CryptoJS.lib.WordArray.random(16);
  const encrypted = CryptoJS.AES.encrypt(message, sharedKey, { iv: iv });
  return {
    iv: iv.toString(CryptoJS.enc.Hex),
    encrypted: encrypted.toString()
};
  // return {
  //     iv: iv.toString(),
  //     encrypted: encrypted.toString()
  // };
}

function decryptMessage(privateKey, publicKey, encryptedData) {
      console.log('decrypt_message')
      const curve = new elliptic.ec('secp256k1');
    const { iv, encrypted } = encryptedData;
    const recipientKey = curve.keyFromPublic(publicKey, 'hex');
    const privKey = curve.keyFromPrivate(privateKey, 'hex');
    const sharedSecret = privKey.derive(recipientKey.getPublic());
    const sharedKey = CryptoJS.enc.Hex.parse(sharedSecret.toString(16).slice(0, 32));

    const decrypted = CryptoJS.AES.decrypt(encrypted, sharedKey, {
        iv: CryptoJS.enc.Hex.parse(iv)
    });

    return decrypted.toString(CryptoJS.enc.Utf8);
}
function sort_for_sign(data) {
  const orderList = [
    'id', 'object_type', 'modelVersion', 'created', 'updated_on_node', 'last_updated', 'func',
    'creatorNodeId', 'validatorNodeId', 'Validator_obj', 'blockchainId', 'Block_obj', 'publicKey', 'Name', 'Title', 'display_name'
  ];

  function stringifyIfBool(value) {
    if (value === true || (typeof value === "string" && value.toLowerCase() === "true")) return "True";
    if (value === false || (typeof value === "string" && value.toLowerCase() === "false")) return "False";
    return value;
  }

  function processValue(value) {
    if (Array.isArray(value)) {
      return value.map(processValue).sort(); // Recursively process & sort lists
    } else if (typeof value === "object" && value !== null) {
      return sort_for_sign(value); // Recursively process objects (nested dicts)
    }
    return stringifyIfBool(value);
  }

  data = Object.fromEntries(Object.entries(data).map(([k, v]) => [k, processValue(v)]));

  const sortedEntries = Object.entries(data).sort(([keyA], [keyB]) => keyA.toLowerCase().localeCompare(keyB.toLowerCase()));

  let sortedObject = Object.fromEntries(sortedEntries);

  const startEntries = orderList
    .filter(key => key in sortedObject)
    .map(key => [key, sortedObject[key]]);

  startEntries.forEach(([key]) => delete sortedObject[key]);

  return Object.fromEntries([...startEntries, ...Object.entries(sortedObject)]);
}
function sortForSign_maybe_try_me(data) {
  const orderList = [
    "id", "object_type", "modelVersion", "created", "updated_on_node", "last_updated", "func",
  ];

  function stringifyIfBool(value) {
    if (value === true || (typeof value === "string" && value.toLowerCase() === "true")) return "True";
    if (value === false || (typeof value === "string" && value.toLowerCase() === "false")) return "False";
    return value;
  }

  function processValue(value) {
    if (Array.isArray(value)) {
      return value
        .map(processValue) // Recursively process each item in the array
        .sort((a, b) => {
          if (typeof a === "object" && a !== null) a = JSON.stringify(a, Object.keys(a).sort());
          if (typeof b === "object" && b !== null) b = JSON.stringify(b, Object.keys(b).sort());
          return a < b ? -1 : a > b ? 1 : 0; // Sort as strings for consistency
        });
    } else if (typeof value === "object" && value !== null) {
      return mySort(value); // Recursively process objects (nested dicts)
    }
    return stringifyIfBool(value);
  }

  data = Object.fromEntries(Object.entries(data).map(([k, v]) => [k, processValue(v)]));

  const sortedEntries = Object.entries(data).sort(([keyA], [keyB]) => keyA.toLowerCase().localeCompare(keyB.toLowerCase()));

  let sortedObject = Object.fromEntries(sortedEntries);

  const startEntries = orderList
    .filter((key) => key in sortedObject)
    .map((key) => [key, sortedObject[key]]);

  startEntries.forEach(([key]) => delete sortedObject[key]);

  return Object.fromEntries([...startEntries, ...Object.entries(sortedObject)]);
}

// // Example Usage:
// const data = {
//   modelVersion: 1.0,
//   id: 123,
//   last_updated: "2025-02-28",
//   blockchainId: "abc123",
//   Title: "Some Title",
//   example: { obj1: [2, 5, 1], obj2: [6, 3, 4] }
// };

// console.log(sortForSign(data));
// function sort_for_sign(data) {
//   const order_list = ['id','object_type','modelVersion','created','created_dt','added','updated_on_node','last_updated','func',
//     'creatorNodeId','validatorNodeId','Validator_obj','blockchainId','Block_obj','publicKey','Name','Title','display_name'
//     ]
//   function stringifyIfBool(value) {
//     if (value === true || (typeof value === "string" && value.toLowerCase() === "true")) {return "True";}
//     if (value === false || (typeof value === "string" && value.toLowerCase() === "false")) {return "False";}
//     return value;
//   }
//   data = Object.fromEntries(Object.entries(data).map(([k, v]) => [k, stringifyIfBool(v)]));
//   const sortedEntries = Object.entries(data).sort(([keyA], [keyB]) => keyA.toLowerCase().localeCompare(keyB.toLowerCase()));
//   let sortedObject = Object.fromEntries(sortedEntries);
//   const startEntries = order_list
//     .filter(key => key in sortedObject)
//     .map(key => [key, sortedObject[key]]);
//   startEntries.forEach(([key]) => delete sortedObject[key]);
//   return Object.fromEntries([...startEntries, ...Object.entries(sortedObject)]);
// }
async function hashMessage(message) {
  const hashHex = CryptoJS.SHA256(message).toString(CryptoJS.enc.Hex);
  return hashHex;
}

async function sign_data(data, privKey=null, pubKey=null) {
  // receives parsed data
  console.log('signing...',data)

  if (pubKey == null) {
    const pubKey = await getKey('pubKey');
  }
    if (privKey == null) {
    const privKey = await getKey('privKey');
  }
  if (privKey == null || privKey == 'null') {
    console.log('privKey nuill')
    return null;
  }

  //   // console.log(pubKey)
  // if (pubKey == null || pubKey == 'null') {
  //   var pubKey = localStorage.getItem("passPubKey");
  //   // console.log('pubKey11aaa',pubKey)
  // }
  // // console.log('privKey11aaa',privKey)
  // if (privKey == null || privKey == 'null') {
  //   var privKey = localStorage.getItem("passPrivKey");
  //   // console.log('privKey11',privKey)
  //   if (privKey == null || privKey == 'null') {
  //     var privKey = localStorage.getItem("bioPrivKey");
  //     // console.log('privKey1122',privKey)
  //   if (privKey == null || privKey == 'null') {
  //       console.log('privKey nuill')
  //       return null;
  //     }
  //   }
  // }
  if ('last_updated' in data) {
    data.last_updated = get_current_time()
  }
  data.publicKey = pubKey
  try {
    delete data.latestModel
  } catch(err){}
  try {
    delete data.signature
  } catch(err){}

  data = sort_for_sign(data);
  data = JSON.stringify(data)
  console.log('siging_data',data)
  // console.log('privKey',privKey)

  // hashed_data1 = await hashMessage(data)
  // console.log('hashed1',hashed_data1)
  // hashed_data2 = await hashMessage(data+' ')
  // console.log('hashed2',hashed_data2)
  // const curve = new elliptic.ec('secp256k1');
  // let keyPair = curve.keyFromPrivate(privKey);
  // const signature = keyPair.sign(hashed_data1, { canonical: true });
  // const sig = signature.toDER('hex');

  hashed_data = await hashMessage(data+'5uHPEF0DPaI4egus4sa6AX')
  // const hashed_data = CryptoJS.SHA256(data).toString(CryptoJS.enc.Hex);
  console.log('hashed_data',hashed_data)
  const curve = new elliptic.ec('secp256k1');
  let keyPair = curve.keyFromPrivate(privKey);
  const signature = keyPair.sign(hashed_data, { canonical: true });
  const sig = signature.toDER('hex');
  console.log("Signature:", sig);
  // return sig

  parsedData = JSON.parse(data)
  // console.log('next')
  parsedData.signature = sig
  // console.log('sig',sig)
  return parsedData
}
async function verify(data, signature, pubKey) {
  console.log('verifing...')
  console.log('signature',signature)
  console.log('pubKey',pubKey)
  const curve = new elliptic.ec('secp256k1');
  let importedPublicKey = curve.keyFromPublic(pubKey, 'hex')
  console.log('importedPublicKey',importedPublicKey)
  hashed_data = await hashMessage(data+'5uHPEF0DPaI4egus4sa6AX')
  // const hashed_data = CryptoJS.SHA256(data).toString(CryptoJS.enc.Hex);
  const isVerified = curve.verify(hashed_data, signature, importedPublicKey);   
  console.log('isVerified',isVerified)  
  return isVerified;
}

async function verifyUserData(userData, localData=false) {
  // receives json.stringify(data)
  x = await getItem('userData')
  console.log('x',x)
  console.log('verify userData')
  console.log('receivedUserData',userData)
  try {
    userData = JSON.parse(userData)
  } catch(err) {}
  console.log('userData',userData)
  receivedPubKey = userData.publicKey
  // localPubKey = receivedPubKey
  if (receivedPubKey == null || receivedPubKey == 'null') {
    console.log('return1')
    return false
  }
  var localPubKey = await getItem("PubKey");
  if (receivedPubKey != localPubKey) {
    // var localPubKey = localStorage.getItem("bioPrivKey");
    // if (receivedPubKey != localPubKey) {
    //   console.log('return2')
      return false;
    // }
  }

  userData.must_rename = false
  var sig = userData.signature
  console.log('sig',sig)
  // var pk = parsedData.publicKey
  // delete userData.modelVersion
  // delete userData.publicKey
  delete userData.signature
  try {
    delete userData.must_rename
  } catch(err){}
  try {
    delete userData.latestModel
  } catch(err){}

  data = sort_for_sign(userData);
  json = JSON.stringify(data)
  console.log('to verify',json)
  is_valid = await verify(json, sig, localPubKey)


  
  return is_valid
}
async function stringTo64CharHash(inputString) {
  // const encoder = new TextEncoder();
  // const data = encoder.encode(inputString);
  // const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  // const hashArray = Array.from(new Uint8Array(hashBuffer));
  // const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  // return hashHex;
  const hashHex = CryptoJS.SHA256(inputString).toString(CryptoJS.enc.Hex);
  return hashHex;
}

async function getKeyPair_old(seed) {
    console.log('get keypair')
    console.log("seed:", seed);
    const curve = new elliptic.ec('secp256k1');
    let keyPair = curve.keyFromPrivate(seed);
    let privKey = keyPair.getPrivate("hex");    
    console.log('privKey',privKey);
    // localStorage.setItem('privKey', privKey);
    // let keyPair2 = curve.keyFromPrivate(privKey);
    // console.log('privKey2',keyPair2.getPrivate("hex"));
    const publicKey = keyPair.getPublic();
    const publicKeyHex = keyPair.getPublic().encode('hex');
    console.log("Public Key:", publicKeyHex);


    // const keyPair = curve.genKeyPair();
        // const privKey = keyPair.getPrivate('hex');
        const pubKey = keyPair.getPublic('hex');
  //   const msg = "testmessage1111";
  //   hashed_data = await hashMessage(msg)
  //   console.log('msg',hashed_data);
  //   const signature = keyPair.sign(hashed_data, { canonical: true });
  //   console.log("Signature:", signature.toDER('hex'));
  // let importedPublicKey = curve.keyFromPublic(publicKeyHex, 'hex')

  //   const isVerified = curve.verify(hashed_data, signature, importedPublicKey);     
  //   console.log("is valid:", isVerified);

    // Decrypt a message

    const message = {'test_dict':'this is a test'};
    const encryptedData = encryptMessage(pubKey, keyPair, JSON.stringify(message));
    const jx = JSON.stringify(encryptedData)
    console.log('Encrypted Data:', jx);

    const decryptedMessage = decryptMessage(privKey, pubKey, JSON.parse(jx));
    console.log('Decrypted Message:', decryptedMessage);


    
    return [privKey, publicKeyHex];
}
function makeAjaxRequest(data, link, item) {
  console.log('makeAjax request')
  return new Promise((resolve, reject) => {
    $.ajax({
      type: 'POST',
      url: link,
      data: data,
      success: function(response) {
        // console.log(item)
        resolve({ response, item });
      },
      error: function(xhr, status, error) {
        console.log('prob1')
        reject(error);
      }
    });
  });
}
async function handleLoginResponse({ response, item }) {
  console.log('handleLoginResponse')
  var password = item
  // console.log(password)
  // console.log(response);
  // console.log(data);
  // console.log(password)
  // $.ajax({
  //   type:'POST',
  //   url:'/accounts/get_user',
  //   data: data,
  //   success: async function(response){
      var field3 = document.getElementById('field3');
      console.log('1')
      message = response['message'];
      console.log(message)
      // receivedUserData = JSON.parse(response['userData']);
      // console.log('11111')
      // d = expand_received_userData(response['userData'])
      // receivedUserData = d[0]
      // receivedUserArrayData = d[1]
      receivedUserData = JSON.parse(response['userData'])
      // console.log('2222')
      // seed = await hashMessage(receivedUserData['id'] + password + receivedUserData['id'] + password + receivedUserData['id'])
      // console.log(seed)
      keyPair = await getKeyPair(receivedUserData['id'], password)
      privKey = keyPair[0]
      pubKey = keyPair[1]

      console.log('keypair', keyPair)
      const postData = {};
      // data['userData'] = userData;
      if (message == 'User not found') {
        postData['publicKey'] = keyPair[1]
        console.log('creating user')
        // walletData = JSON.parse(response['walletData']);
        // walletData = await sign(walletData, privKey=keyPair[0], pubKey=keyPair[1])
        // walletData.signature = walletSignature
        // postData['walletData'] = JSON.stringify(walletData);

        console.log('sign upkData')
        upkData = JSON.parse(response['upkData']);
        upkData['created'] = get_current_time()
        upkData['User_obj'] = receivedUserData['id']
        upkData = await sign_data(upkData, privKey=keyPair[0], pubKey=keyPair[1])
        // upkData.signature = upkSignature
        console.log('signed upkData',upkData)

        postData['upkData'] = JSON.stringify(upkData);
        console.log("postData['upkData']",postData['upkData'])
        userData = receivedUserData
        userData['created'] = get_current_time()
        // userArrayData = receivedUserArrayData
        // if (userData['id'] == 'd704bb87a7444b0ab304fd1566ee7aba') {
        // userData['is_superuser'] = true
        // // userData['is_admin'] = true
        // userData['is_staff'] = true
          // userData['username'] = 'd704bb87a7444b0ab304fd1566ee7aba'
        // }
        console.log('sign sign_userData')
        userData = await sign_userData(userData, privKey=keyPair[0], pubKey=keyPair[1])
        // is_valid = await verifyUserData(userData)
        // console.log('userdata verify:', is_valid)
      } else if ((message == 'User found')) {
        // get_userData_for_sign_return(userData, userArrayData)
        // verify recevied userData against locally stored userdata
        // processedReceivedUserData = get_userData_for_sign_return(receivedUserData, receivedUserArrayData)
        console.log('receivedUserData:',response['userData']);
        stored_userData = get_stored_userData();
        // if () {

          console.log('stored data', stored_userData)
          if (stored_userData != null && stored_userData != 'null' && stored_userData['id'] == receivedUserData['id'] && stored_userData['display_name'] == receivedUserData['display_name']) {
            // if () {
            is_valid = await verifyUserData(response['userData']);
            console.log('userdata verify:', is_valid)
            if (Date(userData['last_updated']) < Date(receivedUserData['last_updated'])) {
              if (is_valid) {
                // userData was updated on a different server more recently than this device
                userData = receivedUserData
                // userArrayData = receivedUserArrayData
                console.log('updated userData from server')
              } else {
                // received data is not valid
                userData = stored_userData
              }
            } else {
              // device userData is up to date
              userData = stored_userData
            }
            // } else {
            //   // receivedUserData does not match local userData
            // }
          } else { 
            // local userData not found
            userData = receivedUserData
            // userArrayData = receivedUserArrayData
            console.log('updated userData from server')
          }
        // }

        // sign_userData(userData, userArrayData)
        postData['publicKey'] = keyPair[1];
        console.log('sign sign_userData', userData)
        userData = await sign_data(userData, privKey=privKey, pubKey=pubKey)
      }
      // console.log(postData['publicKey'])
      // console.log('go')
      // console.log(keyPair[0])
      // console.log()
      // console.log('sign sign_userData')
      // userArrayData.interest_array.push("Rex Murphy Lives")
      // userArrayData.interest_array.push("Rex Murphy 2")
      // userArrayData.follow_post_id_array.push("a0abd5ec79ec5247b6a86a82b28c6d31")
      // userArrayData.follow_post_id_array.push("1d1e9be76e5d360af1e26b162b6c8d51")
      // userArrayData.follow_topic_array.push("Rex Murphy 10")
      // userArrayData.follow_topic_array.push('test')
      // userData = await sign_userData(userData, privKey=keyPair[0], pubKey=keyPair[1])
      // userData = await sign(userData, privKey=keyPair[0], pubKey=keyPair[1])
      // console.log('sig')
      // console.log(signature)
      // // console.log(userData)
      // // parsedData = JSON.parse(userData)
      // userData.signature = signature
      // console.log('2')
      // console.log(JSON.stringify(userData))
      postData['userData'] = JSON.stringify(userData);
      console.log('send to receive user')
      console.log('user_postData',JSON.stringify(userData))
      // field3.innerHTML = 'Username does not match password';
      
      const resp = await connect_to_node('/accounts/receive_user_login', postData);
      console.log('modal response:', resp);
      if (resp) {
        console.log('data received')
        console.log(resp)
          if (resp['message'] == 'Invalid Password') {
              field3.innerHTML = 'Username does not match password';
          } else if (resp['message'] == 'Valid Username and Password'||resp['message'] == 'User Created') {
            console.log('proceed to login')
            // console.log(JSON.stringify(response['userData']))
            
            await storeItem(keyPair[0], 'PrivKey');
            await storeItem(keyPair[1], 'PubKey');
            await storeItem(password, 'password');
            await storeItem(JSON.parse(resp['userData'])['display_name'], 'display_name');
            await storeItem(JSON.parse(resp['userData'])['id'], 'user_id');
            await storeItem(JSON.stringify(userData), 'userData');
            field3.innerHTML = '';
            // localStorage.setItem('passPrivKey', keyPair[0]);
            // localStorage.setItem('passPubKey', keyPair[1]);
            // localStorage.setItem('pass', password);
            // localStorage.setItem('display_name', JSON.parse(response['userData'])['display_name']);
            // localStorage.setItem('user_id', JSON.parse(response['userData'])['id']);
            // localStorage.setItem('userData', JSON.stringify(userData));
            login()
            // modalPopUp('Select Region', '/accounts/get_country_modal')
          } else {
            field3.innerHTML = resp['message']
            // if (response['message'] != 'Valid Username and Password' && response['message'] != 'User Created') {
            // if (response['message'] == 'Verification failed') {
            try {
              display_name = await getItem("display_name")
              pass = await getItem("password")
              if (display_name != 'null' && display_name != null) {
                console.log('create clear button')
                var str_pass = JSON.stringify(pass)
                console.log(str_pass)
                var field4 = document.getElementById('field4');
                field4.innerHTML = `<button id="clearUser" style="color: black;" type="submit" onclick='clearLocalUserData(`+str_pass+`)'>Clear Local User Data</button>`
                
                var field5 = document.getElementById('field5');
                field5.style.display = '';
              }
            } catch(err) {}
            // }
          }
      } else {
        
          console.log('prob2')
          field3.innerHTML = 'Failed to reach server';
          var field5 = document.getElementById('field5');
          field5.style.display = '';
      }
      
      // $.ajax({
      //   type:'POST',
      //   url:'/accounts/receive_user_login',
      //   data: postData,
      //   success: async function(response){
          // console.log(response)
          // if (response['message'] == 'Invalid Password') {
          //     field3.innerHTML = 'Username does not match password'
          // } else if (response['message'] == 'Valid Username and Password'||response['message'] == 'User Created') {
          //   console.log('proceed to login')
          //   // console.log(JSON.stringify(response['userData']))
            
          //   await storeItem(keyPair[0], 'PrivKey');
          //   await storeItem(keyPair[1], 'PubKey');
          //   await storeItem(password, 'password');
          //   await storeItem(JSON.parse(response['userData'])['display_name'], 'display_name');
          //   await storeItem(JSON.parse(response['userData'])['id'], 'user_id');
          //   await storeItem(JSON.stringify(userData), 'userData');

          //   // localStorage.setItem('passPrivKey', keyPair[0]);
          //   // localStorage.setItem('passPubKey', keyPair[1]);
          //   // localStorage.setItem('pass', password);
          //   // localStorage.setItem('display_name', JSON.parse(response['userData'])['display_name']);
          //   // localStorage.setItem('user_id', JSON.parse(response['userData'])['id']);
          //   // localStorage.setItem('userData', JSON.stringify(userData));
          //   login()
          //   // modalPopUp('Select Region', '/accounts/get_country_modal')
          // } else {
          //   field3.innerHTML = response['message']
          //   // if (response['message'] != 'Valid Username and Password' && response['message'] != 'User Created') {
          //   // if (response['message'] == 'Verification failed') {
          //   try {
          //     display_name = await getItem("display_name")
          //     pass = await getItem("password")
          //     if (display_name != 'null' && display_name != null) {
          //       console.log('create clear button')
          //       var str_pass = JSON.stringify(pass)
          //       console.log(str_pass)
          //       var field4 = document.getElementById('field4');
          //       field4.innerHTML = `<button id="clearUser" style="color: black;" type="submit" onclick='clearLocalUserData(`+str_pass+`)'>Clear Local User Data</button>`
          //     }
          //   } catch(err) {}
          //   // }
          // }
        // },
        // error: function (xhr, ajaxOptions, thrownError) {
        //   console.log('prob2')
        //   field3.innerHTML = 'Failed to reach server';
        // } 
      // });
      
}
async function loginAuthenticate(user_data, wallet_data, upk_data, csrf) {
  // console.log(csrf)
  // logout()
  // const json_data = JSON.stringify(user_data)
  var form = document.getElementById("modalForm");
  var username = form.elements["username"].value;
  var password = form.elements["password"].value;
  // console.log("Username:", username);
  // console.log("Password:", password);
  var field0 = document.getElementById('field0');
  var field3 = document.getElementById('field3');
  field0.innerHTML = ''
  if (username == '') {
      field0.innerHTML = 'Please enter a username'
  }else if (password == '') {
      field0.innerHTML = 'Please enter a password'
  // } else if (password.length < 20) {
  //   field0.innerHTML = 'Please enter at least 20 characters in password.'
  } else {
    field3.innerHTML = 'Checking...';

    
    // code = '<div class="lds-dual-ring"></div>'
    // field3.innerHTML = '<div class="lds-dual-ring"></div>';
    // m.querySelector("#modalContent").innerHTML = code;
    var field5 = document.getElementById('field5');
    // field5.innerHTML = '<div class="lds-dual-ring"></div>';
    field5.style.display = 'none';

    const data = user_data;
    data['display_name'] = username
    data['csrfmiddlewaretoken'] = csrf
    // console.log('/accounts/get_user/')
    makeAjaxRequest(data, '/accounts/get_user_login', password)
      .then(handleLoginResponse)
      .catch(error => {
        console.error('There was a problem with the AJAX request:', error);
    });
    
      
  }
}
async function renameUser() {
    
  // const json_data = JSON.stringify(user_data)
  var form = document.getElementById("modalForm");
  var username = form.elements["username"].value;
  // var password = form.elements["password"].value;
  // console.log("Username:", username);
  // console.log("Password:", password);
  var field2 = document.getElementById('field2');
  if (username == '') {
    field2.innerHTML = 'Please enter a username'
  } else {
    // parsedData = JSON.parse(userData)
    d = get_stored_userData()
    userData = d[0]
    userArrayData = d[1]
    userData.display_name = username
    userData.must_rename = false
    userData = get_userData_for_sign_return(userData, userArrayData)
    signedData = await sign_data(userData)
    const data = {};
    // data['display_name'] = username
    // data['must_rename'] = 'False'
    data['userData'] = JSON.stringify(signedData);
    // data['signature'] = signature
    // data['csrfmiddlewaretoken'] = csrf
    $.ajax({
      type:'POST',
      url:'/accounts/receive_rename',
      data: postData,
      success: async function(response){
        console.log(response)
        if (response['message'] == 'Username taken') {
            field2.innerHTML = 'Username not available'
        } else if (response['message'] == 'Success') {
        //     field3.innerHTML = 'Username does not match password'
        // } else if (response['message'] == 'Valid Username and Password'||response['message'] == 'User Created') {
          // console.log('proceed to login')
          // console.log(JSON.stringify(response['userData']))
          // localStorage.setItem('passPrivKey', keyPair[0]);
          // localStorage.setItem('passPubKey', keyPair[1]);
          await storeItem(username, 'display_name');
          await storeItem(JSON.stringify(signedData), 'userData');
          // localStorage.setItem('display_name', username);
          // localStorage.setItem('userData', JSON.stringify(signedData));
          // login()
          location.reload()
          // modalPopUp('Select Region', '/accounts/get_country_modal')
        } else {
          field2.innerHTML = response['message']
        }
      },
      error: function (xhr, ajaxOptions, thrownError) {
        console.log('prob2')
        field2.innerHTML = 'Failed to reach server';
      } 
    });
  }
}
// function parseData(data) {
//   console.log('parse data')
//   parsedData = JSON.parse(data)
//   var result = 
//   for (i in parsedData) {
//     var x = " '" + parsedData[i] + "'"
//     result["'" + i + "'"] = x;
//   }
//   console.log(result)
//   return result
// }
async function handleSigningResponse(userData) {
  console.log('handle sign response')
  if (userData) {
    // console.log(userData)
      parsedData = JSON.parse(userData)
      parsedData = await sign_data(parsedData)
      // console.log('passed sig')
      // parsedData.signature = signature
      result = JSON.stringify(parsedData)
  } else {
    result = null
  }
  return new Promise((resolve, reject) => {
    resolve(result)
  });
}

// not used
async function handleSetRegionResponse(userData) {
  // console.log(userData)
  const data = {'userData': userData};
  // console.log(data)
  // console.log('sending')
  $.ajax({
    type:'POST',
    url:'/accounts/set_user_data',
    data: data,
    success: async function(response){
      if (response['message'] == 'Success') {
        // console.log('success')
        // localStorage.setItem('passPrivKey', passKey);
        // localStorage.setItem('passPubKey', pubKey);
        // localStorage.setItem('username', data['username']);
        await storeItem(userData, 'userData');
        // localStorage.setItem('userData', userData);
        if (window.location.href.indexOf("/region") > -1) {
          // window.location.href = `/region?${queryString}`;
          location.reload()
        } else {
          closeModal();
        }
      } else {
        field3.innerHTML = response['message']
      }
    },
    error: function (xhr, ajaxOptions, thrownError) {
      field3.innerHTML = 'Failed to reach server';
    } 
  });
}
async function setRegionModal(csrf) {
  console.log('setRegionModal')
  code = '<div class="lds-dual-ring"></div>'
  // alert(code)
  var spinner = document.getElementsByClassName("modal-spinner")[0];
  // alert(b)
  spinner.innerHTML = code

  // console.log(csrf)
  // const json_data = JSON.stringify(user_data)
  var form = document.getElementById("modalForm");
  var address = form.elements["address"].value;
  var city = form.elements["city"].value;
  var state = form.elements["state"].value;
  var zip_code = form.elements["zip_code"].value;
  // var password = form.elements["password"].value;
  // console.log("Username:", username);
  // console.log("Password:", password);
  var field2 = document.getElementById('field2');
  field2.innerHTML = ''
  field3.innerHTML = ''
  if (address == '') {
      field2.innerHTML = 'Please enter an address'
  }else if (city == '') {
      field2.innerHTML = 'Please enter a city'
  }else if (state == '') {
      field2.innerHTML = 'Please enter a state'
  } else if (zip_code == '') {
    field2.innerHTML = 'Please enter a zip code'
  } else {
    // user_id = JSON.parse(localStorage.getItem('userData'))['id']
    const data = {};
    country = document.getElementById('field3');
    // console.log(user_id)
    // console.log(country)
    // console.log(country.getAttribute("value"))
    // data['userId'] = user_id;
    data['country'] = country.getAttribute("value");
    data['address'] = address
    data['city'] = city
    data['state'] = state
    data['zip_code'] = zip_code
    data['csrfmiddlewaretoken'] = csrf
    // const utcStr = new Date().toUTCString()
    // Mon, 12 Sep 2022 18:15:18 GMT
    // signature = await sign(utcStr)
    console.log(data)
    // data['regionSetDate'] = utcStr
    // data['setDateSig'] = signature
    console.log('/accounts/set_region_modal')
    $.ajax({
      type: 'POST',
      data: data,
      url: '/accounts/run_region_modal',
      success: function (response) {
        if (response['message'] == 'Failed to set region') {
          field2.innerHTML = response['error']
          spinner.innerHTML = ''
        } else {
          string = '/region'
          resultData = response['result']
          console.log(resultData)
          // federal = resultData['federal']
          function build_url(string, data){
            for (let [key, value] of Object.entries(data)) {
              console.log(key, value);
              for (let item of value) {
                console.log(item);
                string = string + item + '_'
              }
            }
            return string
          }
          string = string + '?roles='
          string = build_url(string, resultData['Federal'])
          // string = string + '?state='
          string = build_url(string, resultData['State'])
          // string = string + '?county='
          string = build_url(string, resultData['County'])
          // string = string + '?city='
          string = build_url(string, resultData['City'])
          window.location.href = string

          // responseData = response['userData']
          // response_json = JSON.parse(responseData)

          // userData, userArrayData = get_stored_userData()
          // userData.Country_obj = response_json['country_id']
          // userData.Federal_District_obj = response_json['federalDistrict_id']
          // userData.ProvState_obj = response_json['provState_id']
          // userData.ProvState_District_obj = response_json['provStateDistrict_id']
          // userData.Greater_Municipality_obj = response_json['greaterMunicipality_id']
          // userData.Greater_Municipal_District_obj = response_json['greaterMunicipalityDistrict_id']
          // userData.Municipality_obj = response_json['municipality_id']
          // userData.Municipal_District_obj = response_json['ward_id']

          // const currentDate = new Date();
          // const isoString = currentDate.toISOString();
          // userData.region_set_date = isoString
          // signedUserData = sign_userData(userData, userArrayData)
          // return_signed_userData(signedUserData)
          // if (window.location.href.indexOf("/region") > -1) {
          //   // window.location.href = `/region?${queryString}`;
          //   location.reload()
          // } else {
          //   closeModal();
          // }


          // console.log(userData)
          // signature = await sign(JSON.stringify(userData))
          // handleSigningResponse(userData)
          //   .then(handleSetRegionResponse)
          //   .catch(error => {
          //     console.error('There was a problem with the AJAX request:', error);
          // });
          // regionData = response['regionData']
          // localStorage.setItem('regionData', regionData);
          // if (window.location.href.indexOf("/region") > -1) {
          //     const responseData = {
          //       // userId: user_id,
          //       // countryId: regionData['country_id'],
          //       // provStateId: regionData['provState_id'],
          //       // regionalMunicipalId: regionData['regionalMunicipality_id'],
          //       // municipalId: regionData['municipality_id'],
          //       // federalDistrictId: regionData['federalDistrict_id'],
          //       // federalDistrictName: regionData['federalDistrict_name'],
          //       // provStateDistrictId: regionData['provStateDistrict_id'],
          //       // regionalMunicipalityDistrictId: regionData['regionalMunicipalityDistrict_id'],
          //       // wardId: regionData['ward_id'],
          //     };
          //     const queryString = new URLSearchParams(responseData).toString();
          //   window.location.href = `/region?${queryString}`;
          // //   location.reload()
          // } else {
          // //   index = document.getElementById('navigation');
          // //   index.innerHTML = '<div class="lds-dual-ring"></div>';
          // //   index = document.getElementById('index');
          // //   index.outerHTML = response;
          //   closeModal();
          // }
        }
      },
      error: function (xhr, ajaxOptions, thrownError) {
        m.querySelector("#modalContent").innerHTML = 'Failed to reach server';
      } 
    });
    
      
  }
}
function remove_region(iden){
  console.log('remove-regino',iden)
  var regions = document.getElementsByClassName("region-reps");
  for (let region of regions) {
    console.log(region.id);
    if (region.id == iden) {
      console.log('remove')
      removeElementWithFadeOut(region)
    }
  }

}
async function save_regions_to_account(userId) {
  console.log('rsave_regions_to_account',userId)
  userData = get_stored_userData()
  console.log(userData)
  var regions = document.getElementsByClassName("region-reps");
  var localities = []
  for (let region of regions) {
    // console.log(region.id);
    var level = region.dataset.level;
    // console.log(level)
    // if (level == 'city') {
    //   level = 'Municipality'
    // }
    var type = region.dataset.type;
    // console.log(type)
    // if (type == 'Region') {
    //   var string = level.charAt(0).toUpperCase() + level.slice(1) + '_obj'
    // } else {
    //   var string = level.charAt(0).toUpperCase() + level.slice(1) + '_' + type.charAt(0).toUpperCase() + type.slice(1) + '_obj'
    // }
    localities.push(region.id)
    // console.log(string + ' = ' + region.id)
    // userData[string] = region.id
    console.log('')
  }
  userData.localities = JSON.stringify(localities)
  const currentDate = new Date();
  const isoString = currentDate.toISOString();
  userData.region_set_date = formatDateToDjango(isoString)
  console.log(JSON.stringify(userData))
  signedUserData = await sign_userData(userData)
  // console.log('signeddata:',signedUserData)
  return_signed_userData(signedUserData)
  

}

function removeElementWithFadeOut(element) {
  element.classList.add('fade-out');
  element.addEventListener('transitionend', () => {
    element.remove();
  });
}


$('#firstPane').scroll(function(){
  sideBarExpand('firstPane')
})
$('#secondPane').scroll(function(){
  sideBarExpand('secondPane')

})
$('#thirdPane').scroll(function(){
  sideBarExpand('thirdPane')

})
$('#fourthPane').scroll(function(){
  sideBarExpand('fourthPane')
})
function sideBarExpand(item) {
  // console.log('item',item)
  var windowPanes = $('.sideBarWindow');
  windowPanes.each(function() {
    if (this.id == item) {
        $(this).addClass('showFullText');
    } else {
      $(this).removeClass('showFullText');
    }
});
}
// function citizenry(){
//   alert('start')
//   $('#citizenry').addClass('showFullText');
//   $('#council').removeClass('showFullText');
//   $('#assembly').removeClass('showFullText');
//   $('#house').removeClass('showFullText');
//   $('#senate').removeClass('showFullText');
// }
// function council(){
//   $('#citizenry').removeClass('showFullText');
//   $('#council').addClass('showFullText');
//   $('#assembly').removeClass('showFullText');
//   $('#house').removeClass('showFullText');
//   $('#senate').removeClass('showFullText');
// }
// function assembly(){
//   $('#citizenry').removeClass('showFullText');
//   $('#council').removeClass('showFullText');
//   $('#assembly').addClass('showFullText');
//   $('#house').removeClass('showFullText');
//   $('#senate').removeClass('showFullText');
// }
// function house(){
//   $('#citizenry').removeClass('showFullText');
//   $('#council').removeClass('showFullText');
//   $('#assembly').removeClass('showFullText');
//   $('#house').addClass('showFullText');
//   $('#senate').removeClass('showFullText');
// }
// function senate(){
//   $('#citizenry').removeClass('showFullText');
//   $('#council').removeClass('showFullText');
//   $('#assembly').removeClass('showFullText');
//   $('#house').removeClass('showFullText');
//   $('#senate').addClass('showFullText');
// }
// $('#citizenry').scroll(function(){
//   alert('1')
//   citizenry()
// })
// $('#council').scroll(function(){
//   council()
// })
// $('#assembly').scroll(function(){
//   assembly()
// })
// $('#house').scroll(function(){
//   house()
// })
// $('#senate').scroll(function(){
//   senate()
// })


function adjustSidebar($el){
  var con = document.getElementById('container');
  var rect = con.getBoundingClientRect();
  var right = rect.left + 1
  right = right.toString()
  right = right + 'px'
$el.css({'position': 'fixed', 'top': '0px', 'right': right }); 
$el.addClass('fixed');
}
function adjustNavBar($navbar){
  var con = document.getElementById('container');
    var rect = con.getBoundingClientRect();
    var right = rect.left + 211
    right = right.toString()
    right = right + 'px'
    $navbar.css({'right': right }); 
    // $navbar.css({'position': 'fixed',  'top': '-1', 'right': right }); 
    $navbar.addClass('fixed');
}

$(window).scroll(function(){ 
  var topics = $('#topics');
  var speakers = $('#speakers');
  var isMobile = document.getElementById('isMobile').name;
    // alert(isMobile)
  if (isMobile != 'True'){
  let window = innerHeight;

  var $navbar = $('#navBar'); 
  // alert($navbar.css('position'))
  // let window = innerHeight;
  var isPositionFixed = ($navbar.css('position') == 'fixed');
  if ($(this).scrollTop() > 72 && !isPositionFixed){
    adjustNavBar($navbar)
  }else if ($(this).scrollTop() < 72 && isPositionFixed){
    var con = document.getElementById('container');
    var rect = con.getBoundingClientRect();
    var right = rect.left 
    right = right.toString()
    right = right + 'px'
    $navbar.css({'right': '-0.5' }); 
    // $navbar.css({'position': 'absolute', 'top':'67.5', 'right': '-0.5' }); 
    $navbar.removeClass('fixed');
  } 
    var $el = $('#sidebar'); 
    // alert($el.html())
    let box = document.querySelector('#sidebar');
    var height = box.offsetHeight;
    // var difference = height - window
    if (height < window){
      // alert('1')
      difference = 100
      var isPositionFixed = ($el.css('position') == 'fixed');
      if ($(this).scrollTop() > 100 && !isPositionFixed){
        adjustSidebar($el)

      }
    }else{
      // alert(difference)
      // difference = height - window + 100
      var isPositionFixed = ($el.css('position') == 'fixed');
      if ($(this).scrollTop() > 100 && !isPositionFixed){
        adjustSidebar($el)
      }
      // alert(difference)
      // difference = height - window + 100
      // var isPositionFixed = ($el.css('position') == 'fixed');
      // if ($(this).scrollTop() > difference && !isPositionFixed){
      //     var con = document.getElementById('container');
      //     var rect = con.getBoundingClientRect();
      //     var right = rect.left - 0
      //     right = right.toString()
      //     right = right + 'px'
      //   $el.css({'position': 'fixed', 'top': window-height-1, 'right': right }); 
      // }
    }
    // alert($(this).scrollTop() )
    // alert(difference)
    if ($(this).scrollTop() < 100 && isPositionFixed){
      $el.css({'position': 'absolute', 'top': '100px', 'right': '1px'}); 
      $el.removeClass('fixed');
    } 
  }
  
  });


//     var isPositionFixed = ($el.css('position') == 'fixed');
//     if ($(this).scrollTop() > 50 && !isPositionFixed){ 
//       $el.css({'position': 'fixed', 'top': '-1px', 'right': '10%'}); 
//     //   alert('sticky')
//     }
//     if ($(this).scrollTop() < 50 && isPositionFixed){
//       $el.css({'position': 'absolute', 'top': '50px', 'right': '0px'}); 
//     //   alert('not sticky')
//     } 
//   });

function shorten_text(cards){
  var isMobile = document.getElementById('isMobile').name;
  try{
    for(i=0; i<cards.length; i++){
      var text = cards[i].getElementsByClassName('Text')[0];
      try{
        if (text) {
          let child = text.parentNode.querySelector('.fadeOut');
          var height = text.offsetHeight;
          if (isMobile == 'True' && height >= 300 && child == null || isMobile == 'False' && height >= 150 && child == null){
            iden = cards[i].id
            code = `<div class='readMore' onclick='continue_reading("` + iden + `", "more")'>Read More</div>`
            $(text).parent().after(code) 
            fade = `<div class='fadeOut' onclick='continue_reading("` + iden + `", "more")'></div>`
            $(text).parent().append(fade) 
        }
        
        }
      }catch(err){}
    }
  }catch(err){}
}
// not used
function get_userData_for_sign_return(userData, userArrayData) {
  // userdata must be processed before sign and before return to server because some fields contain arrays which do not parse properly
  console.log('get_userData_for_sign_return')
  // console.log(userData)
  // console.log(userArrayData.interest_array)
  // userData.interest_array = userArrayData.interest_array
  // userData.follow_post_id_array = userArrayData.follow_post_id_array
  // userData.follow_topic_array = userArrayData.follow_topic_array

  Object.keys(userData).forEach(field => {
    if (field.endsWith('_array')) {
      // console.log('array')
      // console.log(userArrayData[field])
      // console.log(userArrayData[field].replace(/"/g, "'"))
      // userData[field] = userArrayData[field];
        userArrayData[field] = userData[field];
        // userData[field] = JSON.stringify(userArrayData[field]).replace(/"/g, "'");
    }
  });
  // console.log('done1')
  // Object.keys(userArrayData).forEach(field => {
  //   // userData[field] = "['" + userArrayData[field].map(item => item.replace(/'/g, "\\'")).join("', '") + "']";
  //   userData[field] = userArrayData[field];
  // });
  // const arrayString = "['" + userArrayData[field].map(item => item.replace(/'/g, "\\'")).join("', '") + "']";
  // console.log(JSON.stringify(userData))
  return userData

}
function get_current_time(return_string=true) {
  const currentDate = new Date();
  const isoString = currentDate.toISOString();
  if (return_string) {
    return formatDateToDjango(isoString)
  } else {
    return currentDate
  }
}
async function sign_userData(userData, privKey=null, pubKey=null) {
  // receives json.parsed userData
  console.log('sign and return userdata')
  // const currentDate = new Date();
  // const isoString = currentDate.toISOString();
  userData.last_updated = get_current_time()
  delete userData['signature']
  // delete userData['publicKey']

  // parsedData = JSON.parse(userData)
    // parsedData.must_rename = false
    // console.log('must_rename',parsedData.must_rename)
    // delete parsedData.publicKey
    // delete parsedData.signature
    // signed_data = await sign(parsedData)

  // console.log('next11')
    // localStorage.setItem('userData', JSON.stringify(parsedData));
    // get_userData_for_sign_return(userData, userArrayData)
  // }
  // userData = get_userData_for_sign_return(userData, userArrayData)

  // json_data = JSON.parse(userData)
  // console.log('2222', userData)
  // if (privKey && pubKey) {
  userData = await sign_data(userData, privKey=privKey, pubKey=pubKey)
  // } else {
  //   userData = await sign(userData)
  // }
  
  // return_signed_userData(userData)
  console.log('userData222',JSON.stringify(userData))
  return userData
}
function return_signed_userData(userData) {
  console.log('return signed data')
  if (userData) {
    // console.log(JSON.stringify(userData))
    const data = {'userData': JSON.stringify(userData)};
    console.log(data)
    // console.log('sending')
    return new Promise((resolve, reject) => {
      $.ajax({
        type:'POST',
        url:'/accounts/set_user_data',
        data: data,
        success: async function(response){
          console.log(response)
          if (response['message'].toLowerCase() == 'success') {
            console.log('return signed data response 1 success')
            // delete userData['signature']
            // delete userData['publicKey']
            // localStorage.setItem('passPrivKey', passKey);
            // localStorage.setItem('passPubKey', pubKey);
            // localStorage.setItem('username', data['username']);
            await storeItem(JSON.stringify(userData), 'userData');
            // localStorage.setItem('userData', JSON.stringify(userData));
            // if (window.location.href.indexOf("/region") > -1) {
            //   // window.location.href = `/region?${queryString}`;
            //   location.reload()
            // } else {
            //   closeModal();
            // }
          // } else {
          //   field3.innerHTML = response['message']
            console.log('return true')
            resolve(true);
          } else {
            console.log('return signed data response 2',response['message'])
            reject(false);
          }
        },
        error: function (xhr, ajaxOptions, thrownError) {
          console.log('Failed to reach server');
          reject(false);
        } 
      });
    });
  } else {return false}
  
  
}
async function get_stored_userData() {
  // console.log('get stored userdata')
  var userData = JSON.parse(await getItem("userData"));
  return userData
  // console.log(localStorage.getItem("userData"))
  // console.log(JSON.stringify(userData))
  var userArrayData = {};
  // console.log('next')
  try {
    Object.keys(userData).forEach(field => {
      if (field.endsWith('_array')) {
        // console.log(userData[field])
          // userArrayData[field] = userData[field];
        // x.follow_post_id_array = JSON.parse(JSON.stringify(userData.follow_post_id_array).replace(/'/g, '"'));
        userArrayData[field] = JSON.parse(JSON.stringify(userData[field]).replace(/'/g, '"'));
      }
    });
  } catch(err) {}
  // console.log('done get stored data',userArrayData)
  return [userData, userArrayData]
}
// not used
function expand_received_userData(userData) {
  // userData must be processed before local modification becasuse of array fields not parsing properly
  console.log('expand_received_userData')
  var userData = JSON.parse(userData);
  // console.log(userData)
  var userArrayData = {};
  // console.log('next')
  Object.keys(userData).forEach(field => {
    if (field.endsWith('_array')) {
      // console.log(userData[field])
        userArrayData[field] = userData[field];
        // userArrayData[field] = JSON.parse(userData[field].replace(/'/g, '"'));
    }
  });
  Object.keys(userArrayData).forEach(field => {
    // userData[field] = "['" + userArrayData[field].map(item => item.replace(/'/g, "\\'")).join("', '") + "']";
    userData[field] = userArrayData[field];
  });
  
  // const currentDate = new Date();
  // const isoString = currentDate.toISOString();
  
  // console.log('isoString',formatDateToDjango(isoString))
  // console.log('userData.last_updated',userData.last_updated)
  
  // const currentDate2 = new Date(userData.last_updated);
  // const isoString2 = currentDate2.toISOString();
  // console.log('Date(userData.last_updated)',formatDateToDjango(isoString2))
  // userData.last_updated = formatDateToDjango(isoString2)
  // localStorage.setItem('userData', JSON.stringify(userData));
  // console.log('userData11',userData)
  // console.log('userArrayData11',userArrayData)
  return [userData, userArrayData]

}
async function update_userData(receivedUserData) {
  console.log('update_userData')
  // console.log(receivedUserData)
  var parsedReceivedUserData = JSON.parse(receivedUserData);
  var latestModelVersion = parsedReceivedUserData.latestModel;
  // console.log(parsedReceivedUserData)
  if (parsedReceivedUserData.must_rename == true || parsedReceivedUserData.must_rename == 'true') {
    parsedReceivedUserData.must_rename = false
    engage_rename = true
  } else {
    engage_rename = false
  }
  try {
    delete parsedReceivedUserData.must_rename
  } catch(err) {}
  var localUserModelVersion = await getItem("localUserModelVersion");
  // console.log('localUserModelVersion',localUserModelVersion)
  // console.log('parsedReceivedUserData.latestModel',parsedReceivedUserData.latestModel)
  if (latestModelVersion != localUserModelVersion) {
    modelupgrade = true
  } else {
    modelupgrade = false
  }
  try {
    delete parsedReceivedUserData.latestModel
  } catch(err) {}

  async function migrate_userData(fromModel, toModel, send_to_server=true) { 
    Object.keys(toModel).forEach(key => {
      if (fromModel[key]) {
        toModel[key] = fromModel[key]
      }
    });
    toModel['modelVersion'] = latestModelVersion
    if (send_to_server) {
      var signedUserData = await sign_userData(toModel)
      var do_save_data = await return_signed_userData(signedUserData);
    } else {
      do_save_data = true
    }
    if (do_save_data) {
      await storeItem(latestModelVersion, 'localUserModelVersion');
      await storeItem(JSON.stringify(fromModel), 'prev_userData');
      await storeItem(JSON.stringify(userData), 'userData');
      // localStorage.setItem('localUserModelVersion', latestModelVersion); 
      // localStorage.setItem('prev_userData', JSON.stringify(fromModel)); 
      // localStorage.setItem('userData', JSON.stringify(toModel));   

    } 
  }
  is_valid = await verifyUserData(receivedUserData)
  console.log('is_valid',is_valid,'modelupgrade',modelupgrade,'engage_rename',engage_rename)
  if (modelupgrade) {
    console.log('modelupgrade')
    var userData = await get_stored_userData();
    console.log('stroed userData',userData)
    console.log('parsedReceivedUserData',parsedReceivedUserData)
    if ('updated_model' in parsedReceivedUserData) {
      var newUserModel = JSON.parse(JSON.parse(parsedReceivedUserData.updated_model))
      console.log('newUserModel',newUserModel)
      await migrate_userData(userData, newUserModel)

    } else if (is_valid) {
      var userData = get_stored_userData();
      if (Date(userData.last_updated) > Date(parsedReceivedUserData.last_updated)) {
        await migrate_userData(userData, newUserModel)
      } else {
        await storeItem(latestModelVersion, 'localUserModelVersion');
        await storeItem(JSON.stringify(parsedReceivedUserData), 'userData');
        // localStorage.setItem('userData', JSON.stringify(parsedReceivedUserData));   
        // localStorage.setItem('localUserModelVersion', latestModelVersion); 
        console.log('userData updated from server 2') 
      }
    }

    // console.log('done update user')
  } else if (is_valid) {
    var userData = get_stored_userData();
    if (Date(userData.last_updated) < Date(parsedReceivedUserData.last_updated)) {
      await storeItem(JSON.stringify(parsedReceivedUserData), 'userData');
      // localStorage.setItem('userData', JSON.stringify(parsedReceivedUserData));   
      console.log('userData updated from server') 
    } else if (Date(userData.last_updated) > Date(parsedReceivedUserData.last_updated)) {
      return_signed_userData(userData);
    }
    if (engage_rename) {
      modalPopUp('Mandatory User Rename', '/accounts/rename_setup')
    }
  } 
  
}
async function enact_user_instruction(instruction){
  // console.log(instruction)
  if (instruction) {
    
    try {
      var pattern = /^(\w+)\s+(\w+)\s+"([^"]+)"$/;
      var match = pattern.exec(instruction);
      var command = match[1]
      var direction = match[2]
      var target = match[3]
    } catch(err) {
      var command = instruction
    }
    if (command.includes('_array') || command.includes('_json')) {
        // var wordInQuotes = match[1];
        // var direction = instruction.split(' ')[0];
        // console.log(wordInQuotes);
        userData = edit_user_array(command, target, direction)
        userData = sign_userData(userData)
        return_signed_userData(userData)
      //     .then(handleSigningResponse)
      //     .then(return_signed_userData)
      //     .catch(error => {
      //     console.error('There was a problem with the AJAX request:', error);
      // });

        // handleSigningResponse(userData)
        //   .then(handleSetRegionResponse)
        //   .catch(error => {
        //     console.error('There was a problem with the AJAX request:', error);
        // });
    } else if (command == 'get_stored_user_login_data') {
      // console.log('enact get_stored_user_login_data')
      try {
        display_name = await getItem("display_name")
        pass = await getItem("password")
        var form = document.getElementById("modalForm");
        if (display_name != 'null' && display_name != null) {
          form.elements["username"].value = display_name;
        }
        if (pass != 'null' && pass != null) {
          form.elements["password"].value = pass;
        }
        
      } catch(err){}

    }
  }

}

// should be not used
function edit_user_array(array_type, new_keyword, direction){
  console.log('edit user array')
  // console.log(array_type)
  // console.log(direction)
  // console.log(new_keyword)
  // console.log(userData)
  // parsedData = JSON.parse(userData)
  // console.log(parsedData)
  // if (array_type == 'keyword_array'){
  //   array = parsedData.keyword_array
  // } else if (array_type == 'follow_topic_json'){
  //   array = parsedData[array_type]
  // }

  userData = get_stored_userData()
  
  // // parsedData = JSON.parse(userData)
  // // if (array_type == 'keyword_array'){
    interest_array = JSON.parse(userData.interest_array)
  // // } else if (array_type == 'follow_topic_json'){
  //   // follow_topic_json = parsedData.follow_topic_json
    follow_topic_array = JSON.parse(userData.follow_topic_array)
  //   // json_array = 
  // // }
  // console.log(keyword_array)
  // var interest_array = JSON.parse(interest_array.replace(/'/g, '"'));
  // // var follow_topic_json = JSON.parse(follow_topic_json.replace(/'/g, '"'));
  // var follow_topic_array = JSON.parse(follow_topic_array.replace(/'/g, '"'));

  // console.log(follow_topic_json)
  try {
    if (array_type.includes('interest_array')) {
      last_keyword = interest_array[interest_array.length - 1];
      // last_keyword = interest_array[interest_array.length - 1].replace(/^'|'$/g, '');
    } else if (array_type.includes('follow_topic_array')) {
      last_keyword = follow_topic_array[follow_topic_array.length - 1];
      // last_keyword = follow_topic_array[follow_topic_array.length - 1].replace(/^'|'$/g, '');
    }
  }catch(err){
    console.log(err)
    last_keyword = null
  }
  // console.log(last_keyword)
  // console.log(new_keyword)
  if (direction == 'add'){
    if (last_keyword != new_keyword){
      if (array_type.includes('interest_array')) {
        if (interest_array.length > 990) {
          interest_array.shift()
        }
        interest_array.push(new_keyword);
      } else if (array_type.includes('follow_topic_array')) {
        if (follow_topic_array.length > 90) {
          follow_topic_array.shift()
        }
        follow_topic_array.push(new_keyword);
      }
      // console.log('continue')
      // console.log(json_array)
      // // console.log(JSON.stringify(json_array))
      // userData.follow_topic_array = follow_topic_array
      // // parsedData.follow_topic_json = follow_topic_json
      // userData.interest_array = interest_array
      // result = JSON.stringify(parsedData)
    // } else {
    //   // console.log('do not continue')
    //   result = null
    }

  } else if (direction == 'remove'){
    // console.log('remove element')
      if (array_type.includes('interest_array')) {
        var index = interest_array.indexOf(new_keyword);
        if (index !== -1) { 
          interest_array.splice(index, 1);
        }
      } else if (array_type.includes('follow_topic_array')) {
        var index = follow_topic_array.indexOf(new_keyword);
        if (index !== -1) { 
          follow_topic_array.splice(index, 1);
        }
      }

    
      userArrayData.follow_topic_array = follow_topic_array
    // parsedData.follow_topic_json = follow_topic_json
    userArrayData.interest_array = interest_array
    // result = JSON.stringify(parsedData)
    // console.log(JSON.stringify(json_array))
  // } else {
  //   result = null
  }
  userData.follow_topic_array = JSON.stringify(follow_topic_array)
  // parsedData.follow_topic_json = follow_topic_json
  userData.interest_array = JSON.stringify(interest_array)
  return userData
  // console.log('result')
  // console.log(result)
  // return new Promise((resolve, reject) => {
  //   resolve(result)
  // });
}
function formatDateToDjango_old(isoString) {
  const date = new Date(isoString);

  function pad(number, length = 2) {
    return String(number).padStart(length, '0');
  }

  const year = date.getUTCFullYear();
  const month = pad(date.getUTCMonth() + 1);
  const day = pad(date.getUTCDate());
  const hours = pad(date.getUTCHours());
  const minutes = pad(date.getUTCMinutes());
  const seconds = pad(date.getUTCSeconds());
  const milliseconds = pad(date.getUTCMilliseconds(), 3) + '000'; // Add three zeros to match six digits format

  return `${year}-${month}-${day}T${hours}:${minutes}:${seconds}.${milliseconds}+00:00`;
}


async function check_instructions(page) {
  console.log('check instructions')
  // console.log(page)
  try {
    var ud = page.getElementById("userData")
    if (ud) {
      var userData = ud.getAttribute("value")
      await update_userData(userData)
    }
    // console.log('received_data11',userData)
    // userData = get_stored_userData()

    // // is_valid = await verifyUserData(userData)

    // var userData = localStorage.getItem('userData')
    // // d = expand_received_userData(userData)
    // // // parsedData = get_userData_for_sign_return(d[0], d[1])
    // // // // pk = '04a074c0fb97372a462f9e1e840204da9dfcdf9b8cc0a94169b34a1035eb7a82e076350e7108a552adb19c3aad35e42123ab495cb6a1228e83cab55bd582405cf4'
    // // // // sig = '3044022054a17588f60fea91f55c22894b18daee5ce444443eaecb5528132fe45488ec2602202b4ee4ec5ad791360520875312a0dc656b2f95cdd295dd6e06361231f4736596'
    // // // // // pk = parsedData.publicKey
    // // // // // s = parsedData.signature
    // // // // // delete parsedData.publicKey
    // // // // // delete parsedData.signature
    // // // // // console.log('parsedDataa22',JSON.stringify(parsedData))
    // // // // // json = JSON.stringify(parsedData)

    // // // // // is_val = verify(userData, sig, pk)

    // // // // // console.log('2222222')

    // // parsedData = get_userData_for_sign_return(d[0], d[1])
    // // // parsedData.first_name = 'Sozed'
    // // // var s = parsedData.signature
    // // // var pk = parsedData.publicKey
    // // // delete parsedData.publicKey
    // // // delete parsedData.signature
    // // // console.log('signed_data22',JSON.stringify(parsedData))
    // // // json = JSON.stringify(parsedData)

    // // // is_val = await verify(json, s, pk)

    // // userData = d[0]
    // test_data = userData.interest_array
    // parsedTestdata = JSON.parse(test_data)
    // parsedTestdata.push('test1')
    // userData.interest_array = JSON.stringify(parsedTestdata)
    // console.log('test_data',JSON.stringify(parsedTestdata))
    // signed_data = await sign_userData(userData)

    // // // // parsedData = JSON.parse(userData)
    // // // // parsedData.must_rename = false
    // // // // console.log('must_rename',parsedData.must_rename)
    // // // console.log('last_updated', parsedData.last_updated)
    // // // const currentDate = new Date();
    // // // const isoString = currentDate.toISOString();
    // // // // console.log('isoString', isoString)
    // // // parsedData.last_updated = formatDateToDjango(isoString)
    // // // r_lastUpdated = d[0].last_updated
    // // // s_lastUpdated = signed_data.last_updated
    // // // if (Date(r_lastUpdated) > Date(s_lastUpdated)) {
    // // //   console.log('greater')
    // // // } else {
    // // //   console.log('leser')
    // // // }
    // // // delete parsedData.publicKey
    // // // delete parsedData.signature
    // // // signed_data = await sign(parsedData)
    // // // signed_data = await sign_userData(d[0], d[1])
    // // // // // is_valid = await verifyUserData(userData)
    // // console.log('333')
    // // // // localStorage.setItem('userData', JSON.stringify(signed_data))
    // // // // localStorage.setItem('userData', JSON.stringify(signed_data));
    // // // parsedData = JSON.parse(signed_data)
    
    // is_valid = await verifyUserData(JSON.stringify(signed_data))
    // console.log('new valid', is_valid)
    // // // // var modified_data = signed_data
    // // // // // console.log('signed_data11',JSON.stringify(signed_data))
    // // // // pk = signed_data.publicKey
    // // // // s = signed_data.signature
    // // // // delete signed_data.publicKey
    // // // // delete signed_data.signature
    // // // // // console.log('signed_data22',JSON.stringify(signed_data))
    // // // // json = JSON.stringify(signed_data)

    // // // // is_val = verify(json, s, pk)

    // const data = {'userData': JSON.stringify(signed_data)};
    // // console.log('signed_data333',JSON.stringify(signed_data))
    // $.ajax({
    //   type:'POST',
    //   url:'/accounts/set_user_data',
    //   data: data,
    //   success:function(response){
    //     console.log(response)
    //     if (response['message'] == 'success') {
    //       console.log('success')
    //       // delete userData['signature']
    //       // delete userData['publicKey']
    //       // localStorage.setItem('passPrivKey', passKey);
    //       // localStorage.setItem('passPubKey', pubKey);
    //       // localStorage.setItem('username', data['username']);
    //       localStorage.setItem('userData', JSON.stringify(signed_data));
    //       // if (window.location.href.indexOf("/region") > -1) {
    //       //   // window.location.href = `/region?${queryString}`;
    //       //   location.reload()
    //       // } else {
    //       //   closeModal();
    //       // }
    //     // } else {
    //     //   field3.innerHTML = response['message']
    //     } else {
    //       alert(response['message'])
    //     }
    //   },
    //   error: function (xhr, ajaxOptions, thrownError) {
    //     alert('Failed to reach server');
    //   } 
    // });
    
    

    // verifyUserData(userData)
    // console.log('userData:',userData)
    // update_userData(userData)
  }catch(err){console.log('checkinstructions1',err)}
  try{
    var inst = page.getElementById("instruction")
    if (inst) {
      var instruction = inst.getAttribute("value");
  
    // Get the value attribute of the div element
    // var value = divElement
      // var instruction = document.getElementById('instruction');
      // console.log(instruction)
      // console.log(userData)
      enact_user_instruction(instruction)
    }
  }catch(err){
    // console.log(err)
  }
}
function flash_object(element) {
  console.log('flash',element)
  const parentWithClass = element.closest('.cardContainer');
  if (parentWithClass) {
      element = parentWithClass;
  }
  var originalElement = element.cloneNode(true);
  element.style.transition = '0.5s';
  element.classList.add('flash')
  console.log(element)
  setTimeout(function() {
    element.classList.remove('flash')
    setTimeout(function() {
      element.style.removeProperty('transition');
      element.replaceWith(originalElement.cloneNode(true));
      }, 500);
    }, 500);
}


function scrollToElement(element, offsetPercentage=10, flash=false) {
  // console.log('scrollto element', flash, element)
  const elementPosition = element.getBoundingClientRect().top + window.pageYOffset;
  // const offset = window.innerHeight * (offsetPercentage / 100); original setting that worked well
  const offset = window.innerHeight * (offsetPercentage / 100);
  const scrollPosition = elementPosition - offset;

  window.scrollTo({
      top: scrollPosition,
      behavior: 'smooth'
  });
  if (flash) {
    let isScrolling;
  
    window.addEventListener('scroll', function() {
        window.clearTimeout(isScrolling);
  
        isScrolling = setTimeout(function() {
            if (Math.abs(window.pageYOffset - scrollPosition) < 2) {
              flash_object(element)
  
            }
        }, 100);
    }, { passive: true });
  }
}

async function load_queue() {
  console.log('load_queue...',)
  try{
    isLoading = document.getElementsByClassName('lds-dual-ring')[0];
    // alert(isLoading)
    if (isLoading){
      var assignment = await get_assignment(obj=null, iden=null, DateTime=null, nodeIds=[], relevantNodes={});
      console.log('assignment result',assignment)
      addresses = assignment.addresses;
      // broadcastList = assignment.broadcastList;
      orderOfNodes = assignment.orderOfNodes;
      console.log('assignment',orderOfNodes)
      console.log('addresses',addresses)

      current = window.location.href
      // if (current.includes('?')){
      //   addition = '&style=feed'
      // } else {
      //   addition = '?style=feed'
      // }
      const current_path = new URL(current).pathname;
      const current_params = new URL(current).search;
      if (current_params.includes('?')){
        addition = '&style=feed'
      } else {
        addition = '?style=feed'
      }
      url = current + current_path + current_params + addition
      console.log('url1',url);
      // console.log('current_path1',current_path);
      // console.log('current_params1',current_params);
      // console.log('addition3',addition);

      async function fetchWithTimeout(url, timeout = 7000) {
          console.log('fetchWithTimeout',url)
          const controller = new AbortController();
          const signal = controller.signal;
      
          // Set timeout to abort the request
          const timeoutId = setTimeout(() => controller.abort(), timeout);
      
          try {
              const response = await fetch(url, { signal });
              clearTimeout(timeoutId); // Clear timeout on success
              console.log('fetch done1')
              if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
              console.log(`Request: ${response.ok}!`)
              return response;
          } catch (error) {
              if (error.name === "AbortError") {
                  console.log(`Request to ${url} timed out!`);
              } else {
                  console.log(`Fetch failed: ${error.message}`);
              }
              console.log('fetch done2')
              return null; // Indicate failure
          }
      }
      
      async function loopRequests(url, orderOfNodes, addresses) {
        console.log('loopRequests')
        console.log('orderOfNodes',orderOfNodes)
        console.log('addresses',addresses)
        for (let key of orderOfNodes) {
          newIp = addresses[key]
          console.log('newIp',newIp);
          if (!newIp.includes('http')) {
            console.log('add http')
              newIp = 'http://' + newIp;
          } else {
              console.log("The string does not contain 'abc' or 'def'.");
          }
          
          url = newIp + current_path + current_params + addition
          console.log(`Trying: ${url}`);
          const urlObj = new URL(url);
          urlObj.hostname = newIp;
          // console.log('urlObj hostname',urlObj.hostname);

          let result = await fetchWithTimeout(url, 7000);

          if (result) {
              console.log("Success! Processing data:", result);
              // console.log('received data:',data)

              // const feed = document.getElementById('feed');
              const bottomCard = document.getElementById('bottomCard');
              const bottomCardHtml = bottomCard.outerHTML;
              // console.log(bottomCard)
              const delayBetweenCards = 500;
              // var new_cards =  $($.parseHTML(data));
              const feed = $('#feed');




              // Parse the response as text (HTML)
              const htmlText = await result.text();

              // Parse the HTML string to get DOM elements, similar to $.parseHTML(data)
              const parsedElements = $.parseHTML(htmlText); // This returns an array of DOM elements

              // Wrap the parsed elements with jQuery (similar to $(ParsedElements))
              const new_cards = $(parsedElements); // Now newCards is a jQuery object containing the elements

              var newList = new Array();
              for (f = 0; f < new_cards.length; f++){
                // console.log(new_cards[f])
                  newList.push(new_cards[f])
                  feed.append(new_cards[f]);
              }
              document.getElementById("bottomCard").outerHTML='';
              // feed.remove(bottomCard)
              // var newList = new Array();
              function appendAndRevealCards(cards, index = 0, obj, feed, cover = null) {
                // console.log(cover)
                const newCover = $('<div class="cardCover"></div>');
                const newCard = $(cards[index]);
                // console.log(cards[index])

                if (index >= cards.length) {
                  return;
                } 
                // console.log(cards[index])
                var cl = cards[index].className;
                // console.log('cl',cl)
                var iden = cards[index].id;
                if (cl && cl.includes('bottomDivider') || cl && cl.includes('reactionBar') || cl && cl.includes('cardContainer')) {
                  // console.log('append card')
                  obj.push(newCard)
                  // feed.children().eq(-1).before(obj);
                  feed.append(obj);
                  newCard.hide().fadeIn(30, function() {
                    setTimeout(function() {
                      try {
                        cover.fadeOut(30, function() {
                          cover.remove();
                          appendAndRevealCards(cards, index + 1, obj, feed, newCover);
                        });
                      }catch(err) {
                        appendAndRevealCards(cards, index + 1, obj, feed, newCover);
                      }
                    }, 60);
                  });


                } else if (iden && iden.includes('bottomCard')) {
                  // console.log('add bottomcard', cards[index])
                  feed.append(newCard);
                  // newCard.hide().fadeIn(250, function() {
                  //   setTimeout(function() {
                  //     cover.fadeOut(250, function() {
                  //       cover.remove();
                  //       appendAndRevealCards(cards, index + 1, obj, feed, cover);
                  //     });
                  //   }, 500);
                  // });
                } else if (cl && cl.includes('card')) {
                  // console.log('add card')
                  newCard.append(newCover);
                  obj.push(newCard)
                  appendAndRevealCards(cards, index + 1, obj, feed, newCover)
                } else {
                  // console.log('add to obj')
                  // newCard.append(newCover);
                  obj.push(newCard)
                  appendAndRevealCards(cards, index + 1, obj, feed, cover)
                }
              }
              // appendAndRevealCards(newList, 0, [], feed);
              // bottomCard.outerHTML='';
            // console.log('newList',newList)
            // console.log("$('#feed')",$('#feed'))
            document.getElementById("bottomCard").outerHTML='';

            $('#feed').append(newList);
            // bottomCard.outerHTML='';
            page_picker = document.getElementsByClassName('pagePicker');
            page_form = document.getElementById("pageForm");
            try{
              if (page_form) {
                page_form.innerHTML = page_picker[page_picker.length - 1].outerHTML;
              }
            }catch(err){
              // console.log(err)
            }
            var cards = document.getElementsByClassName('card');
            // console.log(cards)
            if (cards['length']) {
              shorten_text(cards)
            } else {
              document.getElementById("bottomCard").outerHTML="<div id='bottomCard'><div style='margin:auto;'>None Found</div></div>";
            }
            try{
              var rePosition = document.getElementsByClassName('moveToHere')[0];
              scrollToElement(rePosition, 10, true);
              
              
            }catch(err){}
            
            var cards = document.getElementsByClassName('card');
            shorten_text(cards)
            // var feed = document.getElementById('feed');
            // // var feedTop = document.getElementsByClassName('feedTop')[0];
            // var feedHeight = feed.offsetHeight;
            // var bottomCard = document.getElementById('bottomCard');
            // var bottomCardHeight = bottomCard.offsetHeight;
            // var sidebar = document.getElementById('sidebar');
            // if (sidebar) {
            //   var sidebarHeight = sidebar.offsetHeight;
            // } else {
            //   var sidebarHeight = 50;
            // }
            // let setHeight = sidebarHeight - (feedHeight - bottomCardHeight) + 50;
            // let windowHeight = (innerHeight);
            // // alert(minHeight)
            // if (feedHeight > windowHeight){
            //   // alert('yes')
            //   // feed.css({'min-height': '110px'}); 
            //   $('#bottomCard').attr("style","min-height:" + setHeight + "; max-height:" + setHeight + ";");
              
            // }
            // var $el = $('#sidebar'); 
            // var isPositionFixed = ($el.css('position') == 'fixed');
            // if ($(this).scrollTop() > 100 && !isPositionFixed){
            //     adjustSidebar($el)
            // }
            // var $navbar = $('#navBar'); 
            // var isPositionFixed = ($navbar.css('position') == 'fixed');
            //   if ($(this).scrollTop() > 70 && !isPositionFixed){
            //     adjustNavBar($navbar)
            //   }
            // break; // Exit loop on first success
            
            }
          else {
            console.log('no result')
          }

        }
          

          // url = current + addition
          // console.log(url)
          // $.ajax({
          //   url: url,
          //   timeout: 7000,
          //   success: function (data) {
          //     console.log('received data:',data)

          //     // const feed = document.getElementById('feed');
          //     const bottomCard = document.getElementById('bottomCard');
          //     const bottomCardHtml = bottomCard.outerHTML;
          //     // console.log(bottomCard)
          //     const delayBetweenCards = 500;
          //       // var new_cards =  $($.parseHTML(data));
          //       const feed = $('#feed');
          //       ParsedElements = $.parseHTML(data);
          //       var new_cards =  $(ParsedElements);
          //       var newList = new Array();
          //       for (f = 0; f < new_cards.length; f++){
          //         // console.log(new_cards[f])
          //           newList.push(new_cards[f])
          //           feed.append(new_cards[f]);
          //       }
          //       document.getElementById("bottomCard").outerHTML='';
          //       // feed.remove(bottomCard)
          //       // var newList = new Array();
          //       function appendAndRevealCards(cards, index = 0, obj, feed, cover = null) {
          //         // console.log(cover)
          //         const newCover = $('<div class="cardCover"></div>');
          //         const newCard = $(cards[index]);
          //         // console.log(cards[index])

          //         if (index >= cards.length) {
          //           return;
          //         } 
          //         // console.log(cards[index])
          //         var cl = cards[index].className;
          //         // console.log('cl',cl)
          //         var iden = cards[index].id;
          //         if (cl && cl.includes('bottomDivider') || cl && cl.includes('reactionBar') || cl && cl.includes('cardContainer')) {
          //           // console.log('append card')
          //           obj.push(newCard)
          //           // feed.children().eq(-1).before(obj);
          //           feed.append(obj);
          //           newCard.hide().fadeIn(30, function() {
          //             setTimeout(function() {
          //               try {
          //                 cover.fadeOut(30, function() {
          //                   cover.remove();
          //                   appendAndRevealCards(cards, index + 1, obj, feed, newCover);
          //                 });
          //               }catch(err) {
          //                 appendAndRevealCards(cards, index + 1, obj, feed, newCover);
          //               }
          //             }, 60);
          //           });


          //         } else if (iden && iden.includes('bottomCard')) {
          //           // console.log('add bottomcard', cards[index])
          //           feed.append(newCard);
          //           // newCard.hide().fadeIn(250, function() {
          //           //   setTimeout(function() {
          //           //     cover.fadeOut(250, function() {
          //           //       cover.remove();
          //           //       appendAndRevealCards(cards, index + 1, obj, feed, cover);
          //           //     });
          //           //   }, 500);
          //           // });
          //         } else if (cl && cl.includes('card')) {
          //           // console.log('add card')
          //           newCard.append(newCover);
          //           obj.push(newCard)
          //           appendAndRevealCards(cards, index + 1, obj, feed, newCover)
          //         } else {
          //           // console.log('add to obj')
          //           // newCard.append(newCover);
          //           obj.push(newCard)
          //           appendAndRevealCards(cards, index + 1, obj, feed, cover)
          //         }
          //       }
          //       // appendAndRevealCards(newList, 0, [], feed);
          //       // bottomCard.outerHTML='';
          //     // console.log('newList',newList)
          //     // console.log("$('#feed')",$('#feed'))
          //     document.getElementById("bottomCard").outerHTML='';

          //     $('#feed').append(newList);
          //     // bottomCard.outerHTML='';
          //     page_picker = document.getElementsByClassName('pagePicker');
          //     page_form = document.getElementById("pageForm");
          //     try{
          //       if (page_form) {
          //         page_form.innerHTML = page_picker[page_picker.length - 1].outerHTML;
          //       }
          //     }catch(err){
          //       // console.log(err)
          //     }
          //     var cards = document.getElementsByClassName('card');
          //     // console.log(cards)
          //     if (cards['length']) {
          //       shorten_text(cards)
          //     } else {
          //       document.getElementById("bottomCard").outerHTML="<div id='bottomCard'><div style='margin:auto;'>None Found</div></div>";
          //     }
          //     try{
          //       var rePosition = document.getElementsByClassName('moveToHere')[0];
          //       scrollToElement(rePosition, 10, true);
                
                
          //     }catch(err){}
          //     },
          //   dataType: 'html'
          // });
        // }
      }
      loopRequests(url, orderOfNodes, addresses);
    }
    console.log('end load queue')
  }catch(err){console.log('load_queue eer2',err)}

}


function formatDateToDjango(isoString) {
  const date = isoString instanceof Date ? isoString : new Date(isoString);
  function pad(number, length = 2) {
      return String(number).padStart(length, '0');
  }
  const year = date.getUTCFullYear();
  const month = pad(date.getUTCMonth() + 1);
  const day = pad(date.getUTCDate());
  const hours = pad(date.getUTCHours());
  const minutes = pad(date.getUTCMinutes());
  const seconds = pad(date.getUTCSeconds());
  const milliseconds = pad(date.getUTCMilliseconds(), 3);
  return `${year}-${month}-${day}T${hours}:${minutes}:${seconds}.${milliseconds}Z`;
}

async function browser_shuffle(text_input, dt, node_ids) {
    console.log('browser_shuffle',text_input,'dt',dt,'node_ids',node_ids);
    async function sha256Hex(input) {
      const encoder = new TextEncoder();
      const data = encoder.encode(input);
      const hashBuffer = await crypto.subtle.digest('SHA-256', data);
      return Array.from(new Uint8Array(hashBuffer))
                  .map(b => b.toString(16).padStart(2, '0'))
                  .join('');
    }
    
    const dt_str = formatDateToDjango(dt);
    const seed_input = `${text_input}_${dt_str}`;

    const hashes = await Promise.all(node_ids.map(async item => {
        const hash = await sha256Hex(seed_input + item);
        return { item, hash };
    }));
    hashes.sort((a, b) => a.hash.localeCompare(b.hash));
    console.log('hashes',hashes)
    return hashes.map(obj => obj.item);
}




async function get_assignment(obj=null, iden=null, DateTime=null, nodeIds=[], relevantNodes={}, region='All') {
  console.log('get_assignment','obj',obj,'iden',iden,'DateTime',DateTime,'nodeIds',nodeIds)
  if (obj != null) {
    if (DateTime == null) {
      var DateTime = obj.DateTime;
    }
    if (iden == null) {
    var iden = obj.iden;
    }
  }
  if (DateTime == null) {
    DateTime = new Date()
  }
  console.log('datetime:',DateTime)
  if (iden == null) {
    var iden = await getItem("user_id");
    console.log('user iden',iden);
    if (!iden) {
      // let uuidHex = crypto.randomUUID().replace(/-/g, "");
      // console.log('uuidHex',uuidHex);
      // iden = 'tusrSo' + uuidHex
      // console.log('temp user iden',iden);
      // localStorage.setItem('user_id', iden);
      
      var iden = await getItem('anonId')
      if (!iden || iden == '0') {
        
        var anonId = document.getElementById("anonId")
        if (anonId.getAttribute("value")) {
          iden = anonId.getAttribute("value");
          // localStorage.setItem('anonId', iden);
          await storeItem(iden, 'anonId');
        } else {
          iden = '0'
        }
      } 
      console.log('temp user iden',iden);
        
    }
  }
  if (nodeIds.length === 0 || Object.keys(relevantNodes).length === 0 ) {
    // console.log('get ids and r_nodes')
    var saved_nodeData = await getItem("nodeData");
    // console.log('saved_nodeData',saved_nodeData)
    var parsed_nodeData = JSON.parse(saved_nodeData);

    // var nodeIds = parsed_nodeData.id_data;
    var relevantNodes = parsed_nodeData.addresses
    if (region !== 'All' && region in parsed_nodeData.id_data) {
      var nodeIds = parsed_nodeData.id_data.region
      // console.log('112',nodeIds);
      if ('servers' in nodeIds) {
        var nodeIds = nodeIds.servers
        // console.log('1123',nodeIds);
      }
    } else {
      var nodeIds = parsed_nodeData.id_data.All
      // console.log('1114',nodeIds);
    }
    // var relevantNodes = parsed_nodeData.address;
  }
  console.log('relevantNodes',relevantNodes)
  console.log('nodeIds',nodeIds)
  const sorted = await browser_shuffle(iden, DateTime, nodeIds);
  console.log('sorted',sorted)
  return {'orderOfNodes':sorted, 'addresses':relevantNodes} ;

  // const sonetInitializedDatetime = new Date(getItem('sonetInitializedDatetime'));
  // // let sonetInitializedDatetime = localStorage.getItem('sonetInitializedDatetime');
  // console.log('sonetInitializedDatetime',sonetInitializedDatetime)


  // // var scraperList = []
  // var orderOfNodes = []
  // var broadcastList = {}
  // var validatorNodes = [] // for transactions only i think
  // // let requiredScrapers = 0
  // let requiredValidators = 500
  // let numberOfPeers = 2

  // dateInt = dateToInt(DateTime, sonetInitializedDatetime);
  // // console.log('dateInt',dateInt)
  // startingPosition = hashToInt(iden, nodeIds.length) + dateInt;
  // // console.log('startingPosition',startingPosition)

  // function reducePos(pos) {
  //   // console.log('reduce',pos)
  //     return pos % nodeIds.length;
  // }

  // let x = reducePos(startingPosition);
  // // checkedNodeList = validatorNodes.map(n => n.id);
  // // console.log('checkedNodeList',checkedNodeList)

  // // x = 0;
  // let run = true;
  // let targetNode = nodeIds[x];

  // while (orderOfNodes.length < requiredValidators && orderOfNodes.length < nodeIds.length && run) {
  //   // console.log('while',x)
  //     try {
  //         let result = process(targetNode, startingPosition, nodeIds, orderOfNodes, broadcastList);
  //         broadcastList = result.broadcastList;
  //         orderOfNodes = result.orderOfNodes;
  //         nodeIds = result.nodeIds;
  //         // console.log('r x orderOfNodes',x,orderOfNodes)
  //         // console.log('orderOfNodes.length',orderOfNodes.length)
  //         // console.log('nodeIds.length',nodeIds.length)
  //         // console.log('requiredValidators',requiredValidators)

  //         // if (func && scrapersOnly) {
  //         //     if (scraperList.length >= requiredScrapers || nodeIds.length === 0) {
  //         //         run = false;
  //         //     }
  //         // }
  //         // if (!broadcastList.hasOwnProperty(targetNode)) {
  //         //     run = false;
  //         // }
  //         x++;
  //         targetNode = orderOfNodes[x];
  //     } catch (e) {
  //       console.log('while err 532',e)
  //         run = false;
  //     }
  // }
  // var addresses = {}
  // for (let i=0; i<orderOfNodes.length; i++) {
  //   addresses[orderOfNodes[i]] = relevantNodes[orderOfNodes[i]];
  // }
  // console.log('return assignment: orderOfNodes',orderOfNodes,'addresses',addresses)
  // return { orderOfNodes, addresses };
}

async function check_for_node_updates(document) {
  console.log('check_for_node_updates')
  var nodeData = document.getElementById("nodeData")
  console.log('nodeData',nodeData.getAttribute("value"))
  if (nodeData.getAttribute("value")) {
    parsed_nodeData = JSON.parse(nodeData.getAttribute("value"))
    console.log('save node data00',parsed_nodeData)
    // localStorage.setItem('nodeData', JSON.stringify(parsed_nodeData));
    var saved_nodeData_str = await getItem("nodeData");
    if (saved_nodeData_str) {
      var saved_nodeData = JSON.parse(saved_nodeData_str);
    } else {
      var saved_nodeData = null;
    }
    console.log('saved node data0', saved_nodeData)
    // console.log('saved node dt', JSON.parse(saved_nodeData)['blockDatetime'])
    if (!saved_nodeData) {
      console.log('save node data1')
      await storeItem(JSON.stringify(parsed_nodeData), 'nodeData');
      // localStorage.setItem('nodeData', JSON.stringify(parsed_nodeData));
    } else if (formatDateToDjango(saved_nodeData['blockDatetime']) < formatDateToDjango(parsed_nodeData['blockDatetime'])) {
      console.log('save node data2')
      await storeItem(JSON.stringify(parsed_nodeData), 'nodeData');
      // localStorage.setItem('nodeData', JSON.stringify(parsed_nodeData));
    } else {
      console.log('no save node data')
    //   console.log('d1',formatDateToDjango(saved_nodeData['blockDatetime']))
    //   console.log('d2',formatDateToDjango(parsed_nodeData['blockDatetime']))
    }
    await storeItem(parsed_nodeData['sonetInitializedDatetime'], 'sonetInitializedDatetime');
    // localStorage.setItem('sonetInitializedDatetime', parsed_nodeData['sonetInitializedDatetime']);

  }
  console.log('done check nodes ')
  // return new Promise((resolve) => setTimeout(resolve, 650));
}

// window.onload = function() {
//   // Set a timeout for the page load process
//   setTimeout(function() {
//     if (document.readyState === "loading" || document.readyState === "interactive") {
//       // Page hasn't finished loading, redirect to other nodes
//       window.location.href = "https://example.com/fallback";
//     }
//   }, 5000); // 5 seconds timeout
// };


// $(document).ready(
//   function(){
//     // alert('document ready start')
//     load_queue()
//     // try{
//     //   isLoading = document.getElementsByClassName('lds-dual-ring')[0];
//     //   // alert(isLoading)
//     //   if (isLoading){
//     //     current = window.location.href
//     //     if (current.includes('?')){
//     //       addition = '&style=feed'
//     //     } else {
//     //       addition = '?style=feed'
//     //     }
//     //     url = current + addition
//     //     console.log(url)
//     //     $.ajax({
//     //       url: url,
//     //       success: function (data) {
//     //         // console.log('received data:',data)

//     //         // const feed = document.getElementById('feed');
//     //         const bottomCard = document.getElementById('bottomCard');
//     //         const bottomCardHtml = bottomCard.outerHTML;
//     //         // console.log(bottomCard)
//     //         const delayBetweenCards = 500;
//     //             // var new_cards =  $($.parseHTML(data));
//     //             const feed = $('#feed');
//     //             ParsedElements = $.parseHTML(data);
//     //             var new_cards =  $(ParsedElements);
//     //             var newList = new Array();
//     //             for (f = 0; f < new_cards.length; f++){
//     //               // console.log(new_cards[f])
//     //                 newList.push(new_cards[f])
//     //                 feed.append(new_cards[f]);
//     //             }
//     //             document.getElementById("bottomCard").outerHTML='';
//     //             // feed.remove(bottomCard)
//     //             // var newList = new Array();
//     //             function appendAndRevealCards(cards, index = 0, obj, feed, cover = null) {
//     //               // console.log(cover)
//     //               const newCover = $('<div class="cardCover"></div>');
//     //               const newCard = $(cards[index]);
//     //               // console.log(cards[index])

//     //               if (index >= cards.length) {
//     //                 return;
//     //               } 
//     //               // console.log(cards[index])
//     //               var cl = cards[index].className;
//     //               // console.log('cl',cl)
//     //               var iden = cards[index].id;
//     //               if (cl && cl.includes('bottomDivider') || cl && cl.includes('reactionBar') || cl && cl.includes('cardContainer')) {
//     //                 // console.log('append card')
//     //                 obj.push(newCard)
//     //                 // feed.children().eq(-1).before(obj);
//     //                 feed.append(obj);
//     //                 newCard.hide().fadeIn(30, function() {
//     //                   setTimeout(function() {
//     //                     try {
//     //                       cover.fadeOut(30, function() {
//     //                         cover.remove();
//     //                         appendAndRevealCards(cards, index + 1, obj, feed, newCover);
//     //                       });
//     //                     }catch(err) {
//     //                       appendAndRevealCards(cards, index + 1, obj, feed, newCover);
//     //                     }
//     //                   }, 60);
//     //                 });


//     //               } else if (iden && iden.includes('bottomCard')) {
//     //                 // console.log('add bottomcard', cards[index])
//     //                 feed.append(newCard);
//     //                 // newCard.hide().fadeIn(250, function() {
//     //                 //   setTimeout(function() {
//     //                 //     cover.fadeOut(250, function() {
//     //                 //       cover.remove();
//     //                 //       appendAndRevealCards(cards, index + 1, obj, feed, cover);
//     //                 //     });
//     //                 //   }, 500);
//     //                 // });
//     //               } else if (cl && cl.includes('card')) {
//     //                 // console.log('add card')
//     //                 newCard.append(newCover);
//     //                 obj.push(newCard)
//     //                 appendAndRevealCards(cards, index + 1, obj, feed, newCover)
//     //               } else {
//     //                 // console.log('add to obj')
//     //                 // newCard.append(newCover);
//     //                 obj.push(newCard)
//     //                 appendAndRevealCards(cards, index + 1, obj, feed, cover)
//     //               }
//     //             }
//     //             // appendAndRevealCards(newList, 0, [], feed);
//     //             // bottomCard.outerHTML='';
//     //         // console.log('newList',newList)
//     //         // console.log("$('#feed')",$('#feed'))
//     //         document.getElementById("bottomCard").outerHTML='';

//     //         $('#feed').append(newList);
//     //         // bottomCard.outerHTML='';
//     //         page_picker = document.getElementsByClassName('pagePicker');
//     //         page_form = document.getElementById("pageForm");
//     //         try{
//     //           if (page_form) {
//     //             page_form.innerHTML = page_picker[page_picker.length - 1].outerHTML;
//     //           }
//     //         }catch(err){
//     //           // console.log(err)
//     //         }
//     //         var cards = document.getElementsByClassName('card');
//     //         // console.log(cards)
//     //         if (cards['length']) {
//     //           shorten_text(cards)
//     //         } else {
//     //           document.getElementById("bottomCard").outerHTML="<div id='bottomCard'><div style='margin:auto;'>None Found</div></div>";
//     //         }
//     //         try{
//     //           var rePosition = document.getElementsByClassName('moveToHere')[0];
//     //           scrollToElement(rePosition, 10, true);
              
              
//     //         }catch(err){}
//     //         },
//     //       dataType: 'html'
//     //   });
//     //   }
      
//     // }catch(err){console.log('eer2',err)}
//     // try{
//     //   var rePosition = document.getElementsByClassName('moveToHere')[0];
//     //   // alert(rePosition)
//     //   rePosition.scrollIntoView({ behavior: 'smooth', block: 'start' });
      
//     // }catch(err){}
    
//     var cards = document.getElementsByClassName('card');
//     shorten_text(cards)
//     var feed = document.getElementById('feed');
//     // var feedTop = document.getElementsByClassName('feedTop')[0];
//     var feedHeight = feed.offsetHeight;
//     var bottomCard = document.getElementById('bottomCard');
//     var bottomCardHeight = bottomCard.offsetHeight;
//     var sidebar = document.getElementById('sidebar');
//     if (sidebar) {
//       var sidebarHeight = sidebar.offsetHeight;
//     } else {
//       var sidebarHeight = 50;
//     }
//     let setHeight = sidebarHeight - (feedHeight - bottomCardHeight) + 50;
//     let windowHeight = (innerHeight);
//     // alert(minHeight)
//     if (feedHeight > windowHeight){
//       // alert('yes')
//       // feed.css({'min-height': '110px'}); 
//       $('#bottomCard').attr("style","min-height:" + setHeight + "; max-height:" + setHeight + ";");
      
//     }
//     // check returned userData, check if more recently updated than local userData, if so check if valid, then save to localStorage
//     // check if userData.must_rename == true, rewrite must_rename to false for verification, perform appropriate action to rename
//     // update_userData(document);
//     check_instructions(document);
//     // alert('done')
//   var $el = $('#sidebar'); 
//   var isPositionFixed = ($el.css('position') == 'fixed');
//   if ($(this).scrollTop() > 100 && !isPositionFixed){
//       adjustSidebar($el)
//   }
//   var $navbar = $('#navBar'); 
//   var isPositionFixed = ($navbar.css('position') == 'fixed');
//     if ($(this).scrollTop() > 70 && !isPositionFixed){
//       adjustNavBar($navbar)
//     }
// }


// )



async function initialize_page(document) {
  console.log('initialize_page')
  masterConnection =  window.location.href

  await check_for_node_updates(document);
  load_queue();
  check_instructions(document);
  console.log('done initialize_page')

}




$(document).ready(
    function(){
      console.log('document ready start');
      initialize_page(document)

      // try{
      //   var rePosition = document.getElementsByClassName('moveToHere')[0];
      //   // alert(rePosition)
      //   rePosition.scrollIntoView({ behavior: 'smooth', block: 'start' });
        
      // }catch(err){}


      // var nodeData = document.getElementById("nodeData")
      // if (nodeData) {
      //   parsed_nodeData = JSON.parse(nodeData)
      //   var saved_nodeData = localStorage.getItem("nodeData");
      //   if (!saved_nodeData) {
      //     localStorage.setItem('nodeData', nodeData);
      //   } else if (formatDateToDjango(saved_nodeData['datetime']) < formatDateToDjango(parsed_nodeData['datetime'])) {
      //     localStorage.setItem('nodeData', nodeData);
      //   }

      //   // var userData = ud.getAttribute("value")
      //   // await update_userData(userData)
      // }

      // masterConnection =  window.location.href

      // await check_for_node_updates(document);
      // load_queue();
      
      // var cards = document.getElementsByClassName('card');
      // shorten_text(cards)
      // var feed = document.getElementById('feed');
      // // var feedTop = document.getElementsByClassName('feedTop')[0];
      // var feedHeight = feed.offsetHeight;
      // var bottomCard = document.getElementById('bottomCard');
      // var bottomCardHeight = bottomCard.offsetHeight;
      // var sidebar = document.getElementById('sidebar');
      // if (sidebar) {
      //   var sidebarHeight = sidebar.offsetHeight;
      // } else {
      //   var sidebarHeight = 50;
      // }
      // let setHeight = sidebarHeight - (feedHeight - bottomCardHeight) + 50;
      // let windowHeight = (innerHeight);
      // // alert(minHeight)
      // if (feedHeight > windowHeight){
      //   // alert('yes')
      //   // feed.css({'min-height': '110px'}); 
      //   $('#bottomCard').attr("style","min-height:" + setHeight + "; max-height:" + setHeight + ";");
        
      // }
      // check returned userData, check if more recently updated than local userData, if so check if valid, then save to localStorage
      // check if userData.must_rename == true, rewrite must_rename to false for verification, perform appropriate action to rename
      // update_userData(document);
      // check_instructions(document);
    //   // alert('done')
    // var $el = $('#sidebar'); 
    // var isPositionFixed = ($el.css('position') == 'fixed');
    // if ($(this).scrollTop() > 100 && !isPositionFixed){
    //     adjustSidebar($el)
    // }
    // var $navbar = $('#navBar'); 
    // var isPositionFixed = ($navbar.css('position') == 'fixed');
    //   if ($(this).scrollTop() > 70 && !isPositionFixed){
    //     adjustNavBar($navbar)
    //   }
    console.log('document ready done');
    // my_test();
  }
)

$(document).on('submit', '#post-form',function(e){
  // alert($('#input-date').val())
  // alert($('#input-date').serialize())
  e.preventDefault();
  $.ajax({
      type:'POST',
      url:'/utils/calendar_widget',
      data: $('#post-form').serialize(),
      // data:{
      //     date:$('#post-form').serialize(),
      //     csrfmiddlewaretoken:$('input[name=csrfmiddlewaretoken]').val(),
      //     action: 'post'
      // },
      success:function(data){
        a = document.getElementById('agenda')
        // alert(a)
        // alert(data)
        a.nextElementSibling.remove()
        a.outerHTML = data
        // alert('done')
        // alert(data)
          // document.getElementById("post-form").reset();
          // $(".posts").prepend('<div class="col-md-6">'+
          //     '<div class="row no-gutters border rounded overflow-hidden flex-md-row mb-4 shadow-sm h-md-250 position-relative">' +
          //         '<div class="col p-4 d-flex flex-column position-static">' +
          //             '<h3 class="mb-0">' + json.title + '</h3>' +
          //             '<p class="mb-auto">' + json.description + '</p>' +
          //         '</div>' +
          //     '</div>' +
          // '</div>' 
          // )
        $('#secondPane').scroll(function(){
          sideBarExpand('secondPane')

        })
      },
      error : function(xhr,errmsg,err) {
      console.log(xhr.status + ": " + xhr.responseText);
  }
  });
});



function mobileSwitch(screen){
  // alert(screen)
    labels = document.getElementsByClassName('label');
    for(i=0;i<labels.length;i++){
      if (labels[i].innerHTML == 'menu'){
        var menu_label = labels[i]
      } else if (labels[i].innerHTML == 'notifications'){
        var notifications_label = labels[i]
      } else if (labels[i].innerHTML == 'mail'){
        var mail_label = labels[i]
      } else if (labels[i].innerHTML == 'search'){
        var search_label = labels[i]
      } 
    }
    var menu = $('.indexMobile');
    var search = $('.searchMobile');
    var notifications = $('.notificationsMobile');
    if (screen == 'menu'){
      if (menu.attr('class').includes('display')){
        menu.removeClass('display');
        menu_label.classList.remove("display_label");
      } else {
        menu.addClass('display');
        menu_label.classList.add("display_label");
        search.removeClass('display');
        search_label.classList.remove("display_label");
        notifications.removeClass('display');
        notifications_label.classList.remove("display_label");
        // $('.feedContainer').removeClass('display');
      }
    } else if (screen == 'search'){
      // alert(search.attr('class'))
      if (search.attr('class').includes('display')){
        search.removeClass('display');
        search_label.classList.remove("display_label");
      } else {
        search.addClass('display');
        search_label.classList.add("display_label");
        menu.removeClass('display');
        menu_label.classList.remove("display_label");
        notifications.removeClass('display');
        notifications_label.classList.remove("display_label");
      }
    }else if (screen == 'feed'){      
      if (menu.attr('class').includes('display') || search.attr('class').includes('display') || notifications.attr('class').includes('display')){
        menu.removeClass('display');
        menu_label.classList.remove("display_label");
        search.removeClass('display');
        search_label.classList.remove("display_label");
        notifications.removeClass('display');
        notifications_label.classList.remove("display_label");
      } else {
        window.location.href = '/';
      }
    } else if (screen == 'notifications'){
      // alert(notifications.attr('class'))
      if (notifications.attr('class').includes('display')){
        notifications.removeClass('display');
        notifications_label.classList.remove("display_label");
      } else {
        notifications.addClass('display');
        notifications_label.classList.add("display_label");
        menu.removeClass('display');
        menu_label.classList.remove("display_label");
        search.removeClass('display');
        search_label.classList.remove("display_label");
      }
    }else if (screen == 'so'){      
      if (menu.attr('class').includes('display') || search.attr('class').includes('display') || notifications.attr('class').includes('display')){
        menu.removeClass('display');
        menu_label.classList.remove("display_label");
        search.removeClass('display');
        search_label.classList.remove("display_label");
        notifications.removeClass('display');
        notifications_label.classList.remove("display_label");
        
      // } else {
      //   window.location.href = '/';
      }
      modal = $('.modalWidget');
      if (modal.hasClass('show')) {
        closeModal()
      } else {
        modalPopUp('So...', 'so_modal')
      }
    }
}

function searchMobileSwitch(tab){
  var tabs = document.getElementsByClassName('searchTab');
  var pages = document.getElementsByClassName('searchTabContent');
  for(i=0; i<pages.length; i++){
    if (pages[i].classList.contains('show')) {
      pages[i].classList.remove('show');
      removePage = pages[i]
        setTimeout(function (){
        removePage.classList.remove('block');
      }, 200);
    }
    if (pages[i].id == tab) {
      pages[i].classList.add('block');
        pages[i].classList.add('show');
    }
  }
  for(i=0; i<tabs.length; i++){
      tabs[i].classList.remove('blue');
    if (tabs[i].id == tab) {
      tabs[i].classList.add('blue');
    }
  }

}


async function my_test() {
  console.log('running my test');
  await key_test();
  console.log('done my test');
}


async function key_test() {
  console.log('runnign key_test');
  // indexedDB.deleteDatabase('KeyDB');
  await storeItem('testme2', 'tester');
  resp = await getItem("PrivKey")
  console.log('PrivKey',resp);
  user_id = await getItem("user_id")
  console.log('user_id',user_id);

  const result1 = await connect_to_node('/utils/is_sonet');
  console.log('Logout response:', result1);

  // const result2 = await connect_to_node('/submit', { user: 'bob', action: 'save' });
  // console.log('Submit response:', result2);


  //     const user_id = "fj8D3h75Hnbe8u";
  //     const user_pass = "jtVE5u8bT&s#";
  //     const message = "hello world";

  //     // Step 1: Generate password and salt
  //     const password = new TextEncoder().encode(user_id + user_pass);
  //     const salt = new TextEncoder().encode(user_id);

  //     // Step 2: Derive private key seed using scrypt
  //     const N = 16384, r = 8, p = 1, dkLen = 32;
  //     const seed = await scrypt(password, salt, N, r, p, dkLen);
  //     const seedHex = Array.from(seed).map(b => b.toString(16).padStart(2, '0')).join('');
  //     console.log("Private key seed (hex):", seedHex);

  //     // Step 3: Create secp256k1 keypair
  //     const ec = new elliptic.ec('secp256k1');
  //     const keyPair = ec.keyFromPrivate(seedHex);

  //     const privateKeyHex = keyPair.getPrivate("hex");
  //     const publicKeyHex = keyPair.getPublic().encode("hex"); // uncompressed
  //     console.log("Private Key (hex):", privateKeyHex);
  //     console.log("Public Key (hex, uncompressed):", publicKeyHex);

  //     // Step 4: Sign message with SHA-256 hash
  //     const msgHash = CryptoJS.SHA256(message).toString(CryptoJS.enc.Hex);
  //     const signature = keyPair.sign(msgHash, { canonical: true });
  //     const signatureDERHex = signature.toDER("hex");

  //     console.log("Message:", message);
  //     console.log("Message Hash (SHA-256, hex):", msgHash);
  //     console.log("Signature (DER, hex):", signatureDERHex);
  console.log('done key_test');
}



// import { scrypt } from 'scrypt-js';
// import elliptic from 'elliptic';
// async function create_key() {
//   console.log('create_key');


//   const user_id = 'fj8D3h75Hnbe8u';
//   const user_pass = 'jtVE5u8bT&s#';

//   // Step 1: Prepare password and salt
//   const password = new TextEncoder().encode(user_id + user_pass);
//   const salt = new TextEncoder().encode(user_id); // Deterministic salt

//   console.log("Password (text):", user_id + user_pass);
//   console.log("Password (bytes):", Array.from(password));
//   console.log("Salt (text):", user_id);
//   console.log("Salt (bytes):", Array.from(salt));

//   // Step 2: Derive a 32-byte seed using scrypt
//   const N = 16384, r = 8, p = 1, dkLen = 32;

//   scrypt(password, salt, N, r, p, dkLen).then(seed => {
//     const seedHex = Buffer.from(seed).toString('hex');
//     console.log("Derived Seed (hex):", seedHex);

//     // Step 3: Generate keypair from seed
//     const curve = new elliptic.ec('secp256k1');
//     const keyPair = curve.keyFromPrivate(seed);
//     const privKeyHex = keyPair.getPrivate('hex');
//     const pubKeyHex = keyPair.getPublic().encode('hex');

//     console.log("Private Key:", privKeyHex);
//     console.log("Public Key:", pubKeyHex);
  
//   });
// }

