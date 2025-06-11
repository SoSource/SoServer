
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect, Http404
# from django.utils.text import slugify
from django.template.defaulttags import register
from django.views.decorators.csrf import csrf_exempt

from django.contrib.auth import (
    authenticate,
    get_user_model,
    login,
    logout,

    )

# from scrapers.canada.federal import get_federal_match

from .models import User, UserPubKey, UserVote
from .forms import *
from posts.models import Region, Post
from posts.utils import get_user_data
from posts.forms import SearchForm
from posts.views import render_view
from blockchain.models import Sonet
from utils.locked import hash_obj_id, get_signing_data
from utils.models import *
from django.http import JsonResponse, HttpResponse, HttpRequest

# from fcm_django.models import FCMDevice
# from firebase_admin.messaging import Message, Notification
from django.db.models import Q, Value, F
# import auth_token
import os
import datetime
import requests
import json
from bs4 import BeautifulSoup
import time
from uuid import uuid4
import operator
import ast

# @register.filter
# def get_item(dictionary, key):
#     return dictionary.get(key)

# headers = {
#     'User-Agent': "OOrss-get"
# } 

def privacy_policy_view(request):
    style = request.GET.get('style', 'index')
    context = {
        'title': 'Privacy Policy',
        'cards': 'privacyPolicy',
    }
    return render_view(request, context)
    
def values_view(request):
    style = request.GET.get('style', 'index')
    context = {
        'title': 'Values',
        'cards': 'values',
    }
    return render_view(request, context)

def hero_view(request):
    style = request.GET.get('style', 'index')
    context = {
        'title': 'So You want to be a Hero?',
        'cards': 'hero',
    }
    return render_view(request, context)

def about_view(request):
    style = request.GET.get('style', 'index')
    context = {
        'title': 'About Us',
        'cards': 'about',
    }
    return render_view(request, context)

def contact_view(request):
    style = request.GET.get('style', 'index')
    context = {
        'title': 'Contact',
        'cards': 'contact',
    }
    return render_view(request, context)

def get_app_view(request):
    style = request.GET.get('style', 'index')
    context = {
        'title': 'Get the App',
        'cards': 'getApp',
    }
    return render_view(request, context)

def story_view(request):
    style = request.GET.get('style', 'index')
    context = {
        'title': 'A So-So Story',
        'cards': 'story',
    }
    return render_view(request, context)

def signup_view(request):
    prnt('signup view')
    user_obj = User()
    user_obj.initialize()
    context = {
        'title': 'Login',
        'user_dict': get_signing_data(user_obj),
    }
    return render(request, "forms/signup.html", context)


# step 1 user login/signup
def login_signup_view(request):
    prnt('login signup view')
    user_obj = User()
    user_obj.initialize()
    context = {
        'title': 'Login',
        'user_dict': get_signing_data(user_obj),
    }
    return render(request, "forms/login-signup.html", context)

def login_signup_super_view(request):
    prnt('super user dev create view')
    if not User.objects.first() and not Sonet.objects.first():
        user_obj = User()
        user_obj.initialize()
        from utils.locked import generate_id
        user_obj.id = 'usrSo' + generate_id('ShardHolder')
        context = {
            'title': 'Login/Signup',
            'user_dict': get_signing_data(user_obj),
        }
        return render(request, "forms/login-signup.html", context)

def rename_setup_view(request):
    prnt('rename_setup view')
    # user_id = uuid.uuid4().hex
    # wallet_id = uuid.uuid4().hex
    # upk_id = uuid.uuid4().hex
    # dt = now_utc()
    # user_obj = User(id=user_id, username=user_id, created=dt)
    context = {
        'title': 'Mandatory User Rename',
        'text': 'Unfortunately your username was previously registered and must be replaced.',
        # 'user_dict': get_signing_data(user_obj),
        # 'wallet_dict': get_signing_data(wallet_obj),
        # 'upk_dict': get_signing_data(upk_obj),
    }
    # prnt('n2')
    return render(request, "forms/must_rename.html", context)

@csrf_exempt
def receive_rename_view(request):
    prnt('receive_rename_view')
    if request.method == 'POST':
        # received_json = request.POST
        # prnt(received_json)
        # prnt()
        userData = request.POST.get('userData')
        prnt(userData)
        userData_json = json.loads(userData)
        
        try:
            User.objects.filter(display_name=userData_json['display_name']).exclude(id=userData_json['id'])[0]
            return JsonResponse({'message':'Username taken'})
        except:
            
            user = request.user
            # data is verified during sync
            user, synced = sync_and_share_object(user, userData)
            prnt('synced',synced)
            user.slug = user.slugger()
            user.save()
            if synced:
                return JsonResponse({'message':'success'})
            else:
                return JsonResponse({'message':'Failed to sync'})
    return JsonResponse({'message':'Failed'})

# not used
def register_options_view(request):
    prnt('register options')
    from webauthn import (
        generate_registration_options,
        verify_registration_response,
        options_to_json,
        base64url_to_bytes,
    )
    from webauthn.helpers.cose import COSEAlgorithmIdentifier
    from webauthn.helpers.structs import (
        AttestationConveyancePreference,
        AuthenticatorAttachment,
        AuthenticatorSelectionCriteria,
        PublicKeyCredentialDescriptor,
        ResidentKeyRequirement,
    )



    user_id = uuid.uuid4().hex
    dt = datetime.datetime.now()
    prnt(user_id.encode())
    # prnt(bytes(user_id))
    # salt = os.urandom(16)
    user_obj = User(id=user_id, created=dt)
    # options_obj = UserOptions(id=uuid.uuid4().hex, user=user_id, created=dt, salt=salt)
    # userForm = UserRegisterForm(request.POST or None)

    simple_registration_options = generate_registration_options(
        rp_id='localhost',
        rp_name="SoVote",
        user_name="bob",
        user_id='679563c4a4214dc2ba7b6cb5896757f2'.encode(),
    )

    prnt(options_to_json(simple_registration_options))
    return JsonResponse(json.loads(options_to_json(simple_registration_options)))

# not used
def verify_transaction(transaction_data, signature):
    from ecdsa import SECP256k1, VerifyingKey, BadSignatureError, util
    import hashlib

    try:

        # Create a verifying key from the public key (assuming it's the compressed form of the key)
        # verifying_key = VerifyingKey.from_public_key_recovery(signature, SECP256k1, hashlib.sha256, util.sigdecode_string(signature, SECP256k1.order)[0] - 27)
        verifying_key = VerifyingKey.from_public_key_recovery(signature, SECP256k1, hashlib.sha256)  # The last argument is the hashing algorithm

        # Verify the signature
        is_verified = verifying_key.verify_digest(signature, bytes.fromhex(transaction_data), sigdecode=util.sigdecode_string)
        return is_verified
    

        # # Create a verifying key from the public key (assuming it's the compressed form of the key)
        # verifying_key = VerifyingKey.from_public_key_recovery(signature, SECP256k1, hashlib.sha256, util.sigdecode_string(signature, SECP256k1.order)[0] - 27)

        # # Verify the signature
        # is_verified = verifying_key.verify_digest(signature, to_buffer(transaction_data), sigdecode=util.sigdecode_string)
        # return is_verified

    except BadSignatureError:
        return False
    


    # # from ethereum.utils import ecrecover, pub_to_address, to_buffer, to_checksum_address, from_rpc_sig
    # from ethereum.utils import ecrecover, pub_to_address, to_buffer, to_checksum_address, from_rpc_sig, sha3

    # # In this example, I assume the transaction_data is the hash of the transaction
    # transaction_hash = sha3(to_buffer(transaction_data))

    # # Perform Ethereum signature verification
    # try:
    #     public_key = ecrecover(transaction_hash, signature.v, signature.r, signature.s)
    #     sender_address = to_checksum_address(pub_to_address(public_key))
        
    #     # Compare sender_address with the expected fromAddress or perform additional checks if needed
    #     expected_sender_address = 'YourFromAddress'
    #     return sender_address == expected_sender_address

    # except Exception as e:
    #     prnt(f"Error during signature verification: {e}")
    #     return False

# not used
def get_user_data_view(request, username):
    prnt('get user data view')
    try:
        user_obj = User.objects.filter(username=username)[0]
        return JsonResponse({'message' : 'User found', 'userData' : get_signing_data(user_obj)})
    except:
        user_id = uuid.uuid4().hex
        dt = datetime.datetime.now()
        user_obj = User(id=user_id, username=username, created=dt)
    # context = {
    #     'user_dict': get_signature_data(user_obj)
    # }
    # return render_view(request, context)
    x = get_signing_data(user_obj)
    # prnt(x)
    return JsonResponse(x)
    # return render(request, "utils/dummy.html", {'result': x})
# not used
def register_verify_view(request):

    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.asymmetric import ec
    import hashlib

    prnt('verify view')
    # prnt(request.body)
    prnt()
    import base64
    # prnt(request.POST)
    prnt('1')
    # elem = base64.b64decode(request.POST)
    # prnt(request.body.decode())
    # prnt(elem)
    received_json = request.POST
    prnt(received_json)
    # for i in received_json:
    #     prnt(i)
    #     prnt(received_json[i])
    prnt()
    prnt(received_json['publicKeyHex'])
    prnt()
    prnt('td', str(received_json['transactionData']))
    prnt()
    # prnt('privKey received',received_json['privateKey'])
    prnt()
    prnt(str(received_json['signature']))
    # prnt()
    # prnt(received_json['r'])
    # prnt()
    # prnt(received_json['s'])
    # from ethereum.utils import ecrecover, pub_to_address, to_buffer, to_checksum_address, from_rpc_sig
    from ecdsa import SECP256k1, VerifyingKey, BadSignatureError, util

    # signed_tx_data = request.POST.get('signedData')
    # prnt(signed_tx_data)
    # privateKey = request.POST.get('privateKey')
    publicKey = request.POST.get('publicKeyHex')
    transaction_data = request.POST.get('transactionData')
    signature = request.POST.get('signature')
    # r = request.POST.get('r')
    # s = request.POST.get('s')
    # signature = ['48', '68', '2', '32', '75', '213', '151', '71', '233', '42', '173', '36', '183', '158', '166', '10', '106', '120', '212', '39', '50', '167', '38', '155', '126', '181', '25', '253', '206', '34', '83', '133', '14', '214', '31', '255', '2', '32', '34', '43', '162', '192', '13', '128', '84', '45', '29', '73', '173', '198', '201', '81', '84', '42', '206', '249', '189', '189', '198', '13', '167', '13', '144', '63', '177', '244', '12', '6', '101', '139']
    # signature = ''.join(signature)
    # prnt(signature)
    prnt()

    samplepubkey = '04f8ccf508990ceef9e5b84f5aeb9fee1739d3d3b140fc05e5b2ff58524c660ba27f654ed36fe7dd9923a1ffaf5caa774c2e9fd18ffb486432f44914c22c29eccf'
    samplesig = '3044022010f92d4771aac187375265167f43854d510428a131124df798b406a5dcc7eab5022029bbadf9aa6b4741d7fed01999121fe34ad8b2216f7200d953904bbd271d84e0'
    sampler = '10f92d4771aac187375265167f43854d510428a131124df798b406a5dcc7eab5'
    samples = '29bbadf9aa6b4741d7fed01999121fe34ad8b2216f7200d953904bbd271d84e0'

    nextpubkey= 'MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEKFCwY4ysc/3EvJWfYhhmrg3qSzz1qiradgh+QH/P44eWTUq0v5HKbIbIMPdHSZb6pSjCnniBrwHMwVC3bM6VBQ=='
    nextsig = 'DlScOm5IU7/DFdN5wI/WBJNhIp4yJAKzsttmrxsOIduKbTgn53zBsqsKqd7qw0A9I7GjDkxLhyBE78EXND04Ug=='

    from ecdsa import SECP256k1, VerifyingKey

    # Received signature and public key from JavaScript
    signature_hex = "..."
    public_key_hex = "..."

    # Decode public key
    public_key = VerifyingKey.from_string(bytes.fromhex(publicKey), curve=SECP256k1)

    # Prepare data (replace with the same data used in JavaScript)
    data = "Transaction data"
    # hash = bytes.fromhex(require('crypto').createHash('sha256').update(data).digest('hex'))
    message = b"testmessage"

    # Verification
    try:
        if public_key.verify(bytes.fromhex(signature), message):
            prnt("Signature is valid!")
        else:
            prnt("Signature is invalid!")
    except Exception as e:
        prnt(str(e)) 
        prnt("Verification failed!")


    # import ecdsa
    # from ecdsa.util import sigencode_der
    # from hashlib import sha256
    # message = b"testmessage"
    # public_key = '98cedbb266d9fc38e41a169362708e0509e06b3040a5dfff6e08196f8d9e49cebfb4f4cb12aa7ac34b19f3b29a17f4e5464873f151fd699c2524e0b7843eb383'
    # sig = '740894121e1c7f33b174153a7349f6899d0a1d2730e9cc59f674921d8aef73532f63edb9c5dba4877074a937448a37c5c485e0d53419297967e95e9b1bef630d'
    # # sig = '3045022010f92d4771aac187375265167f43854d510428a131124df798b406a5dcc7eab5022100d64452065594b8be28012fe666ede01b6fd62ac53fd69f626c4212cfa918bc61'
    # # sig = '10f92d4771aac187375265167f43854d510428a131124df798b406a5dcc7eab529bbadf9aa6b4741d7fed01999121fe34ad8b2216f7200d953904bbd271d84e0'
    # sig = r + s

    # vk = ecdsa.VerifyingKey.from_string(bytes.fromhex(publicKey), curve=ecdsa.SECP256k1) # the default is sha1
    # # vk = ecdsa.VerifyingKey.from_string(bytes.fromhex(public_key), curve=ecdsa.SECP256k1, hashfunc=sha256) # the default is sha1
    
    # from ecdsa.util import sigdecode_der
    # # signature_bytes = util.sigdecode_der(bytes.fromhex(signature), vk.pubkey.order)
    # # assert vk.verify(bytes.fromhex(signature), message, hashlib.sha256, sigdecode=sigdecode_der)
    # # assert vk.verify(signature, message, hashlib.sha256, sigdecode=sigencode_der)
    # is_valid = vk.verify(bytes.fromhex(sig), message) # True

    # # def verify_transaction(public_key, signature, message):
    # #     from ecdsa.util import sigdecode_der
    # #     vk = VerifyingKey.from_string(bytes.fromhex(public_key), curve=SECP256k1)
    # #     prnt('vk', vk)
    # #     # signature_bytes = bytes.fromhex(signature)
    # #     # signature_bytes = bytes.fromhex(signature)
    # #     # signature_bytes = util.sigdecode_der(signature, vk.pubkey.order)
    # #     return vk.verify(signature, message.encode('utf-8'))
    # #     # return vk.verify(signature_bytes, message.encode('utf-8'), hashlib.sha256, sigdecode=sigdecode_der)
    # # # Replace these values with the corresponding values from your JavaScript code
    # # public_key_hex = publicKey
    # # signature_der_hex = signature
    # # # transaction_data = "Message"

    # # # Verify the transaction
    # # # message_hash = hash_message(transaction_data)
    # # is_valid = verify_transaction(public_key_hex, signature_der_hex, transaction_data)

    # if is_valid:
    #     prnt("Transaction is valid!")
    # else:
    #     prnt("Transaction is not valid.")




# --------this one works

    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
    from cryptography.hazmat.primitives.serialization import load_der_public_key
    from cryptography.hazmat.primitives import hashes
    from cryptography.exceptions import InvalidSignature
    import base64
    import json



    publicKey = base64.b64decode(publicKey)
    # data = {
    # "data_1":"The quick brown fox",
    # "data_2":"jumps over the lazy dog"
    # }
    # data = "jumps over the lazy dog1111"
    # prnt('d', data)
    prnt('td', transaction_data)
    data = transaction_data
    signature = base64.b64decode(signature)

    publicKey = load_der_public_key(publicKey, default_backend())
    r = int.from_bytes(signature[:32], byteorder='big')
    s = int.from_bytes(signature[32:], byteorder='big')

    try:
        publicKey.verify(
            encode_dss_signature(r, s),
            json.dumps(data, separators=(',', ':')).encode('utf-8'),
            ec.ECDSA(hashes.SHA256())    
        )
        prnt("verification succeeded")
    except InvalidSignature:
        prnt("verification failed")

# # -------------




    # publikKeyDer = base64.b64decode(publicKey)
    # # publikKeyDer = base64.b64decode("MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEWzC5lPNifcHNuKL+/jjhrtTi+9gAMbYui9Vv7TjtS7RCt8p6Y6zUmHVpGEowuVMuOSNxfpJYpnGExNT/eWhuwQ==")
    # # data = "jumps over the lazy dog"
    # prnt('trans_data', transaction_data)
    # # prnt('data', data)
    # signature = base64.b64decode(signature)
    # # signature = base64.b64decode("XRNTbkHK7H8XPEIJQhS6K6ncLPEuWWrkXLXiNWwv6ImnL2Dm5VHcazJ7QYQNOvWJmB2T3rconRkT0N4BDFapCQ==")

    # publicKey = load_der_public_key(publikKeyDer, default_backend())
    # r = int.from_bytes(signature[:32], byteorder='big')
    # s = int.from_bytes(signature[32:], byteorder='big')

    # try:
    #     publicKey.verify(
    #         encode_dss_signature(r, s),
    #         json.dumps(transaction_data).encode('utf-8'),
    #         ec.ECDSA(hashes.SHA256())    
    #     )
    #     prnt("verification succeeded")
    # except InvalidSignature:
    #     prnt("verification failed")






    # import hashlib
    # from ecdsa import SigningKey, SECP256k1, VerifyingKey

    def hash_message(message):
        sha256 = hashlib.sha256()
        sha256.update(message.encode('utf-8'))
        return sha256.hexdigest()

    # def verify_transaction(public_key, signature, message):
    #     from ecdsa.util import sigdecode_der
    #     vk = VerifyingKey.from_string(bytes.fromhex(public_key), curve=SECP256k1)
    #     # signature_bytes = bytes.fromhex(signature)
    #     signature_bytes = bytes.fromhex(signature)
    #     # signature_bytes = util.sigdecode_der(bytes.fromhex(signature), vk.pubkey.order)
    #     return vk.verify(signature_bytes, message.encode('utf-8'))
    #     # return vk.verify(signature_bytes, message.encode('utf-8'), hashlib.sha256, sigdecode=sigdecode_der)
    # # Replace these values with the corresponding values from your JavaScript code
    # public_key_hex = publicKey
    # signature_der_hex = signature
    # transaction_data = "Message"

    # # Verify the transaction
    # message_hash = hash_message(transaction_data)
    # is_valid = verify_transaction(public_key_hex, signature_der_hex, message_hash)

    # if is_valid:
    #     prnt("Transaction is valid!")
    # else:
    #     prnt("Transaction is not valid.")





    # from cryptography.hazmat.primitives.serialization import load_der_private_key
    # # def sign_transaction(private_key, message):
    # #     private_key_obj = ec.derive_private_key(
    # #         int(private_key, 16),
    # #         ec.SECP256K1(),
    # #         default_backend()
    # #     )
    # #     prnt('priv key discoverd:', private_key)
    # #     signature = private_key_obj.sign(
    # #         message,
    # #         ec.ECDSA(hashes.SHA256())
    # #     )
    # #     return signature
    
    # def sign_transaction(private_key_hex, message):
    #     private_key_obj = ec.derive_private_key(
    #         int(private_key_hex, 16),
    #         ec.SECP256K1(),
    #         default_backend()
    #     )
    #     prnt('priv key discovered:', private_key_hex)
    #     signature = private_key_obj.sign(
    #         message,
    #         ec.ECDSA(hashes.SHA256())
    #     )
    #     return signature
    # privKey = '97ddae0f3a25b92268175400149d65d6887b9cefaf28ea2c078e05cdc15a3c0a'
    # message_bytes = str.encode('Message')
    # transaction_signature = sign_transaction(privKey, message_bytes)
    # prnt('!!!!!', transaction_signature.hex())

    # prnt('sig', signature)


    # message_bytes = str.encode(transaction_data)
    # private_key_bytes = str.encode(privateKey)
    # prnt('riv_key_bytes', private_key_bytes)



    # prnt('done')
    # # Message that was signed
    # message = transaction_data.encode()

    # # Convert the public key and signature values to bytes
    # public_key_bytes = bytes.fromhex(publicKey)
    # signature_bytes = bytes.fromhex(transaction_signature.hex())
    
    # # Create an Elliptic Curve Public Key object
    # public_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), public_key_bytes)
    # prnt('pubkey', public_key)
    # # Verify the signature
    # try:
    #     public_key.verify(signature_bytes, message_bytes, ec.ECDSA(hashes.SHA256()))
    #     prnt("Signature is valid.")
    # except Exception as e:
    #     prnt(str(e))
    #     prnt("Signature is invalid.")


    # from ecdsa import SigningKey
    # from ecdsa.curves import SECP256k1
    # ecdsakey = "59b1ad799522457fa5ed171cb850800fe511e55181d81250e66d42ff536427a1"
    # sk = SigningKey.from_string(bytes.fromhex(privateKey), curve=SECP256k1)
    # hash = "b93b25c03a2238e749272a99d8a47dbcc19c2db65b9b27671f1ec6b5defd279b"
    # # prnt(hash)
    # signature_bytes = bytes.fromhex(signature)
    # prnt('sig0', signature_bytes)
    # prnt()
    # signature_bytes = bytes.fromhex(r + s)
    # prnt('sig1', signature_bytes)
    # prnt()
    # # hash = codecs.decode(hash, 'hex')
    # message = str.encode('9a59efbc471b53491c8038fd5d5fe3be0a229873302bafba90c19fbe7d7c7f35')
    # sig = sk.sign_deterministic(message)
    # prnt('sig2', sig)
    # prnt()
    # vk = sk.get_verifying_key()
    # prnt(vk.verify(sig, message))










    # from ecdsa import SigningKey, SECP256k1, VerifyingKey
    # import hashlib

    # # Create an elliptic curve object for secp256k1
    # ec = SECP256k1

    # # Generate key pair or load from private key
    # private_key_hex = "97ddae0f3a25b92268175400149d65d6887b9cefaf28ea2c078e05cdc15a3c0a"
    # key_pair = SigningKey.from_string(bytes.fromhex(private_key_hex), curve=ec)

    # # Get private key and public key
    # priv_key = key_pair.to_string().hex()
    # pub_key = key_pair.get_verifying_key()

    # prnt(f"Private key: {priv_key}")
    # prnt("Public key:", pub_key.to_string().hex()[2:])
    # prnt("Public key (compressed):", pub_key.to_string("compressed").hex())





    # import ecdsa
    # import hashlib

    # # Convert the public key and signature values to bytes
    # public_key_bytes = bytes.fromhex(publicKey)
    # signature_bytes = bytes.fromhex(signature)
    # prnt('sig', signature_bytes)
    # # message_hash = hash_message(transaction_data)

    # message = str.encode(transaction_data)
    # prnt(message)
    # # from .curves import NIST192p, Curve, Ed25519, Ed448
    # # Create a VerifyingKey object from the public key bytes
    # vk = VerifyingKey.from_string(public_key_bytes, curve=ecdsa.SECP256k1)
    # try:
    #     # Verify the signature
    #     vk.verify(signature_bytes, message)
    #     prnt("Signature is valid.")
    # except BadSignatureError:
    #     prnt("Signature is invalid.")

    # import ecdsa
    # import hashlib





    # # Replace 'your_private_key_hex' with your actual private key
    # your_private_key_hex = "your_private_key_here"
    # priv_key = ecdsa.SigningKey.from_string(bytes.fromhex(privateKey), curve=ecdsa.SECP256k1)

    # # Replace 'inputted_public_key_hex' with the inputted public key
    # inputted_public_key_hex = "inputted_public_key_here"
    # inputted_pub_key = ecdsa.VerifyingKey.from_string(bytes.fromhex(publicKey), curve=ecdsa.SECP256k1)
    # prnt('pubkey', inputted_pub_key)


    # message = b"Message"
    # message = str.encode(transaction_data)
    # prnt(message)
    # message_hash = hashlib.sha256(message).digest()
    # signature1 = priv_key.sign(message_hash)
    # prnt("The signature is:\n", signature1)
    # prnt()
    # signature1 = bytes.fromhex(signature)
    # prnt("The signature is:\n", signature1)

    # try:
    #     inputted_pub_key.verify(signature1, message_hash)
    #     prnt("Signature verified: True")
    # except ecdsa.BadSignatureError:
    #     prnt("Signature verified: False")
    # except Exception as e:
    #     prnt(str(e))
    # prnt()



    # from ellipticcurve.ecdsa import Ecdsa
    # from ellipticcurve.privateKey import PrivateKey


    # # Generate new Keys
    # # privateKey = PrivateKey()
    # # prnt(privateKey)
    # # publicKey = privateKey.publicKey()
    # # prnt(publicKey)

    # message = "My test message"
    # prnt(message)
    # # Generate Signature
    # signature = Ecdsa.sign(message, privateKey)
    # prnt('sig', signature)

    # # To verify if the signature is valid
    # prnt(Ecdsa.verify(message, signature, publicKey))


    # import ecdsa
    # prnt()
    # from ecdsa import VerifyingKey, SECP256k1

    # # def verifySignature(dataToVerify, signatureBase64, publicKeyPem):
    # #     # Decode signature from base64
    # #     signature = bytes.fromhex(signatureBase64)
        
    # #     verifying_key = VerifyingKey.from_pem(publicKeyPem, curve=SECP256k1)
    # #     return verifying_key.verify(signature, dataToVerify)
    # from hashlib import sha256
    # # Example usage
    # data = b"Message"
    # # signatureBase64 = base64.b64decode(signature)  # Replace with the base64 encoded signature from JavaScript
    # publicKeyPem = publicKeyHex  # Replace with your public key in PEM format
    # is_valid = ecdsa.verify(data, signature, publicKeyHex, hashfunc=sha256)
    # # is_valid = verifySignature(data, signature, publicKeyPem)
    # prnt(f"Signature is valid: {is_valid}")
    # # Sign a message
    # msg = b'Message'
    # signature = key_pair.sign(msg, hashfunc=hashlib.sha256)

    # prnt(f"Msg: {msg.decode()}")
    # prnt("Signature:", signature.hex())

    # prnt()
    # import ecdsa
    # import hashlib
    # # your_private_key_hex = "97ddae0f3a25b92268175400149d65d6887b9cefaf28ea2c078e05cdc15a3c0a"
    # # priv_key = ecdsa.SigningKey.from_string(bytes.fromhex(your_private_key_hex), curve=ecdsa.SECP256k1)


    # # priv_key = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
    # # public_key = priv_key.get_verifying_key()


    # # Replace 'inputted_public_key_hex' with the inputted public key
    # inputted_public_key_hex = "inputted_public_key_here"
    # public_key = ecdsa.VerifyingKey.from_string(bytes.fromhex(publicKeyHex), curve=ecdsa.SECP256k1)
    # prnt(public_key)
    # prnt(bytes.fromhex(signature))

    # message = b"Message"
    # message_hash = hashlib.sha256(message).digest()
    # prnt('1')
    # # signature = priv_key.sign(message_hash)
    # # prnt("The signature is:\n",signature)
    # try:
    #     public_key.verify(bytes.fromhex(signature), message_hash)
    #     prnt("Signature verified: True")
    # except ecdsa.BadSignatureError:
    #     prnt("Signature verified: False")
    # Recover public key from signature
    # def hex_to_decimal(x):
    #     return int(x, 16)

    # pub_key_recovered = VerifyingKey.from_public_point(
    #     hex_to_decimal(pub_key.to_string().hex()[-64:]), curve=ec)

    # prnt("Recovered pubKey:", pub_key_recovered.to_string("compressed").hex())

    # Verify the signature
    # valid_sig = pub_key_recovered.verify(signature, msg, hashfunc=hashlib.sha256)

    # prnt("Signature valid?", valid_sig)
    # public_key = base64.b64decode(publicKeyHex)
    # prnt(public_key)
    # # Hash the transaction data
    # digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
    # digest.update(transaction_data.encode('utf-8'))
    # hashed_transaction = digest.finalize()

    # from cryptography.hazmat.primitives.asymmetric import ec
    # # # Verify the signature using the public key
    # try:
    #     pub_key.verify(signature.hex(), msg, ec.ECDSA(hashes.SHA256()))
    #     prnt('valid')
    # except Exception as e:
    #     prnt(f"Signature verification failed: {str(e)}")
    #     # return False  # Verification failed



    # import ecdsa
    # from hashlib import sha256
    # message = b"Message"
    # public_key = '98cedbb266d9fc38e41a169362708e0509e06b3040a5dfff6e08196f8d9e49cebfb4f4cb12aa7ac34b19f3b29a17f4e5464873f151fd699c2524e0b7843eb383'
    # sig = '740894121e1c7f33b174153a7349f6899d0a1d2730e9cc59f674921d8aef73532f63edb9c5dba4877074a937448a37c5c485e0d53419297967e95e9b1bef630d'


    # from ecdsa.util import sigdecode_der
    # # assert vk.verify(signature, data, hashlib.sha256, sigdecode=sigdecode_der)

    # vk = ecdsa.VerifyingKey.from_string(bytes.fromhex(publicKeyHex), curve=ecdsa.SECP256k1, hashfunc=sha256) # the default is sha1
    # vk.verify(bytes.fromhex(signature), message, hashlib.sha256, sigdecode=sigdecode_der) # True
    # prnt('verify', vk.verify(bytes.fromhex(signature), message, hashlib.sha256, sigdecode=sigdecode_der))
    
    
    
    
    # s = request.POST.get('s')
    # r = request.POST.get('r')
    # v = request.POST.get('v')

    # Reconstruct the signature
    # r = signed_tx_data[0]
    # s = signed_tx_data[1]
    # v = signed_tx_data[2]
    # prnt(r)
    # prnt(s)
    # signature = util.sigdecode_string(bytes.fromhex(r + s), SECP256k1.order)  # Convert r and s to a DER-encoded signature
    # # signature = util.sigdecode_string(to_buffer(r + s), SECP256k1.order)  # Convert r and s to a DER-encoded signature

    # # Perform verification logic
    # is_verified = verify_transaction(transaction_data, signature)

    # # if is_verified:
    # prnt('verified', is_verified)
    
    # import ecdsa
    # from hashlib import sha256
    # message = b"message"
    # public_key = '98cedbb266d9fc38e41a169362708e0509e06b3040a5dfff6e08196f8d9e49cebfb4f4cb12aa7ac34b19f3b29a17f4e5464873f151fd699c2524e0b7843eb383'
    # sig = '740894121e1c7f33b174153a7349f6899d0a1d2730e9cc59f674921d8aef73532f63edb9c5dba4877074a937448a37c5c485e0d53419297967e95e9b1bef630d'

    # vk = ecdsa.VerifyingKey.from_string(bytes.fromhex(publicKeyHex), curve=ecdsa.SECP256k1, hashfunc=sha256) # the default is sha1
    # verify = vk.verify(bytes.fromhex(signature), message) # True
    # prnt('verify', verify)
    # signed_tx_data = request.data.get('signedData')
    # transaction_data = request.data.get('transactionData')

    # # Reconstruct the signature
    # r = signed_tx_data['r']
    # s = signed_tx_data['s']
    # v = signed_tx_data['v']
    # signature = from_rpc_sig(to_buffer(r), to_buffer(s), to_buffer(v))
    # prnt('sig', signature)
    # # Perform verification logic
    
    # # Perform verification logic
    # is_verified = verify_transaction(transaction_data, signature)
    # prnt('verified', is_verified)

    # # Process the transaction if verification is successful
    # # Your custom logic here...

    # return JsonResponse({'status': 'success', 'verification_result': True})


    # if request.method == 'POST':
    #     # Get data from the POST request
    #     public_key_hex = request.POST.get('publicKeyHex')
    #     signature_hex = request.POST.get('signature')
    #     transaction_data = request.POST.get('transactionData')

    #     # Convert hexadecimal public key to bytes
    #     public_key_bytes = bytes.fromhex(public_key_hex)

    #     # Convert hexadecimal signature to bytes
    #     signature_bytes = bytes.fromhex(signature_hex)

    #     # Create an ECDSA public key object
    #     public_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), public_key_bytes)

    #     # Verify the signature
    #     try:
    #         public_key.verify(signature_bytes, transaction_data.encode('utf-8'), ec.ECDSA(hashes.SHA256()))
    #         prnt('is valid')
    #         return JsonResponse({'result': 'Signature is valid'})
    #     except Exception as e:
    #         prnt(str(e))
    #         prnt('is not valid')
    #         return JsonResponse({'result': 'Signature is not valid'})

    # # Handle other HTTP methods or return an error response if needed
    # return JsonResponse({'error': 'Invalid request method'})



    # data = received_json
    # public_key_hex = data['publicKeyHex']
    # signature_hex = data['signature']
    # transaction_data = data['transactionData']

    # # Convert hexadecimal public key to bytes
    # public_key_bytes = bytes.fromhex(public_key_hex)

    # # Convert hexadecimal signature to bytes
    # signature_bytes = bytes.fromhex(signature_hex)

    # # Create an ECDSA public key object
    # public_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), public_key_bytes)

    # # Verify the signature
    # try:
    #     public_key.verify(signature_bytes, transaction_data.encode('utf-8'), ec.ECDSA(hashes.SHA256()))
    #     prnt({'result': 'Signature is valid'})
    # except:
    #     prnt({'result': 'Signature is not valid'})




    # from cryptography.hazmat.primitives import hashes
    # from cryptography.hazmat.backends import default_backend
    # from cryptography.hazmat.primitives.asymmetric import ec

    # # Replace these values with the corresponding values from the JavaScript code
    # public_key_hex = received_json['publicKeyHex'].replace('"', '')  # The public key in hexadecimal format
    # signature_hex = received_json['signature'].replace('"', '')  # The signature in hexadecimal format
    # transaction_data = received_json['transactionData']

    # # Convert hexadecimal public key to bytes
    # public_key_bytes = bytes.fromhex(public_key_hex)

    # # Convert hexadecimal signature to bytes
    # signature_bytes = bytes.fromhex(signature_hex)

    # # Create an ECDSA public key object
    # public_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), public_key_bytes)

    # # Verify the signature
    # try:
    #     public_key.verify(signature_bytes, transaction_data.encode('utf-8'), ec.ECDSA(hashes.SHA256()))
    #     prnt('Signature is valid.')
    # except:
    #     prnt('Signature is not valid.')









    #     from webauthn import (
    #         generate_registration_options,
    #         verify_registration_response,
    #         options_to_json,
    #         base64url_to_bytes,
    #     )
    #     from webauthn.helpers.cose import COSEAlgorithmIdentifier
    #     from webauthn.helpers.structs import (
    #         AttestationConveyancePreference,
    #         AuthenticatorAttachment,
    #         AuthenticatorSelectionCriteria,
    #         PublicKeyCredentialDescriptor,
    #         ResidentKeyRequirement,
    #     )


    # # 1
    # # {'id': 'AZ3rpIpPFHA75irNXUDf4mbGo5oBJ4Lbm-haWsRNhyWGSANDmzxVfK0CHMa5IYtxTujPJMnidL2dO9eNWZmfGs4', 'rawId': 'AZ3rpIpPFHA75irNXUDf4mbGo5oBJ4Lbm-haWsRNhyWGSANDmzxVfK0CHMa5IYtxTujPJMnidL2dO9eNWZmfGs4', 'response': {'attestationObject': 'o2NmbXRkbm9uZWdhdHRTdG10oGhhdXRoRGF0YVjFSZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2NFAAAAAAAAAAAAAAAAAAAAAAAAAAAAQQGd66SKTxRwO-YqzV1A3-JmxqOaASeC25voWlrETYclhkgDQ5s8VXytAhzGuSGLcU7ozyTJ4nS9nTvXjVmZnxrOpQECAyYgASFYIKijphsXKur5xaXF8QOpfU6IddY8KvqqZxcN35hSYMCCIlggeRbMkdLQi43wF9YIuC7ES3tB29xIgJGZO8H2QFJ-V_o', 'clientDataJSON': 'eyJ0eXBlIjoid2ViYXV0aG4uY3JlYXRlIiwiY2hhbGxlbmdlIjoiUGFDVkhOUlp1ZU9fTU1jdnlHcV82aXJ1NGdmSkZWU3BPdktwSGRGTGpXQURsakFHRG1FeC1OMnpQUGhHZ1VwUnpVR21tb3RPQ0Z5TkhqVVdCT2pNc2ciLCJvcmlnaW4iOiJodHRwOi8vbG9jYWxob3N0OjMwMDUiLCJjcm9zc09yaWdpbiI6ZmFsc2UsIm90aGVyX2tleXNfY2FuX2JlX2FkZGVkX2hlcmUiOiJkbyBub3QgY29tcGFyZSBjbGllbnREYXRhSlNPTiBhZ2FpbnN0IGEgdGVtcGxhdGUuIFNlZSBodHRwczovL2dvby5nbC95YWJQZXgifQ', 'transports': ['hybrid', 'internal'], 'publicKeyAlgorithm': -7, 'publicKey': 'MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEqKOmGxcq6vnFpcXxA6l9Toh11jwq-qpnFw3fmFJgwIJ5FsyR0tCLjfAX1gi4LsRLe0Hb3EiAkZk7wfZAUn5X-g', 'authenticatorData': 'SZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2NFAAAAAAAAAAAAAAAAAAAAAAAAAAAAQQGd66SKTxRwO-YqzV1A3-JmxqOaASeC25voWlrETYclhkgDQ5s8VXytAhzGuSGLcU7ozyTJ4nS9nTvXjVmZnxrOpQECAyYgASFYIKijphsXKur5xaXF8QOpfU6IddY8KvqqZxcN35hSYMCCIlggeRbMkdLQi43wF9YIuC7ES3tB29xIgJGZO8H2QFJ-V_o'}, 'type': 'public-key', 'clientExtensionResults': {}, 'authenticatorAttachment': 'cross-platform'}
        
    #     registration_verification = verify_registration_response(
    #         # Demonstrating the ability to handle a plain dict version of the WebAuthn response
    #         credential=received_json,
    #         # expected_challenge=base64url_to_bytes(
    #         #     "CeTWogmg0cchuiYuFrv8DXXdMZSIQRVZJOga_xayVVEcBj0Cw3y73yhD4FkGSe-RrP6hPJJAIm3LVien4hXELg"
    #         # ),
    #         # expected_origin="http://localhost:5000",
    #         # expected_rp_id="localhost",
    #         # require_user_verification=True,
    #     )

    #     prnt("\n[Registration Verification - None]")
    #     prnt(registration_verification)
    #     # assert registration_verification.credential_id == base64url_to_bytes(
    #     #     "ZoIKP1JQvKdrYj1bTUPJ2eTUsbLeFkv-X5xJQNr4k6s"
    #     # )
    #     return JsonResponse(json.loads(registration_verification))

# not used
def register_view(request):
    prnt('register view')
    prnt(request.user.is_authenticated)
    style = request.GET.get('style', 'index')
    title = "Sign Up"
    cards = 'register'

    prnt()
    prnt(request)
    # from webauthn import (
    #     generate_registration_options,
    #     verify_registration_response,
    #     options_to_json,
    #     base64url_to_bytes,
    # )
    # from webauthn.helpers.cose import COSEAlgorithmIdentifier
    # from webauthn.helpers.structs import (
    #     AttestationConveyancePreference,
    #     AuthenticatorAttachment,
    #     AuthenticatorSelectionCriteria,
    #     PublicKeyCredentialDescriptor,
    #     ResidentKeyRequirement,
    # )

    # simple_registration_options = generate_registration_options(
    #     rp_id="sovote.org",
    #     rp_name="SoVote",
    #     user_name="bob",
    # )

    # prnt(options_to_json(simple_registration_options))










    user_id = uuid.uuid4().hex
    dt = datetime.datetime.now()
    salt = os.urandom(16)
    user_obj = User(id=user_id, created=dt)
    # options_obj = UserOptions(id=uuid.uuid4().hex, user=user_id, created=dt, salt=salt)
    userForm = UserRegisterForm(request.POST or None)
    # optionsForm = UserOptionsRegisterForm(request.POST or options_obj)

    # user = userForm.save(commit=False)
    # # options = optionsForm.save(commit=False)
    # # prnt(user)
    # #password = form.cleaned_data.get('password')
    # # import re
    # pattern = re.compile("[A-Za-z0-9+_-]+")
    # # email = optionsForm.cleaned_data.get('email')
    # password = userForm.cleaned_data.get('password')
    # password_confirm = userForm.cleaned_data.get('password_confirm')
    # if userForm.is_valid():
    #     if not pattern.fullmatch(user.username):
    #         userForm.add_error('username', 'Only A-Z, 0-9, +, _, or - allowed')
    #     elif email == None:
    #         # prnt(form.errors)
    #         userForm.add_error('email', 'Please enter an email address')
        
    #     elif '@' not in email:
    #         # raise forms.ValidationError("Passwords must match")
    #         # prnt(form.errors)
    #         userForm.add_error('email', 'Please enter a valid email address')
    #     elif password != password_confirm:
    #         # raise forms.ValidationError("Passwords must match")
    #         # prnt(form.errors)
    #         userForm.add_error('password', 'Passwords must match')
    #     else:
    #         # prnt('else')
    #         try:
    #             user_name = UserOptions.objects.filter(display_name=user.username)[0]
    #             userForm.add_error('username', 'Username already taken')
    #         except:

                
    #             if userForm.signature and optionsForm.signature:
    #                 prnt('has sigs')
    #                 from blockchain.models import get_signature_data
    #                 # verfiy userForm
    #                 public_key = base64.b64decode(optionsForm['public_key'])
    #                 digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
    #                 digest.update(str(get_signature_data(userForm)).encode('utf-8'))
    #                 hashed_transaction = digest.finalize()
    #                 try:
    #                     public_key.verify(userForm['signature'], hashed_transaction, ec.ECDSA(hashes.SHA256()))
    #                     userForm_is_valid = True
    #                 except Exception as e:
    #                     prnt(f"Signature verification failed: {str(e)}")
    #                     userForm_is_valid = False
    #                 # verify optionsForm
    #                 # public_key = base64.b64decode(optionsForm['public_key'])
    #                 digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
    #                 # digest.update(str(get_signature_data(optionsForm)).encode('utf-8'))
    #                 hashed_transaction = digest.finalize()
    #                 # try:
    #                 #     public_key.verify(optionsForm['signature'], hashed_transaction, ec.ECDSA(hashes.SHA256()))
    #                 #     optionsForm_is_valid = True
    #                 # except Exception as e:
    #                 #     prnt(f"Signature verification failed: {str(e)}")
    #                 #     optionsForm_is_valid = False
                    
    #                 # if optionsForm_is_valid and userForm_is_valid:
    #                 #     # try: 
    #                 #     #     u = UserOptions.objects.filter(email=email)[0]
    #                 #     #     # prnt(form.errors)
    #                 #     #     userForm.add_error('email', 'Email is already in use')
    #                 #     # except Exception as e:`
    #                 #     # prnt(str(e))
    #                 #     # try:
    #                 #     #     userToken = request.COOKIES['userToken']
    #                 #     # except:
    #                 #     #     userToken = None
    #                 #     # if userToken:
    #                 #     #     try:
    #                 #     #         anon_user = User.objects.filter(userToken=userToken, anon=True)[0]
    #                 #     #         anon_user.anon = False
    #                 #     #         anon_user.username = user.username
    #                 #     #         anon_user.email = user.email
    #                 #     #         user = anon_user
    #                 #     #     except:
    #                 #     #         pass
    #                 #     user.set_password(password)
    #                 #     user.save()
    #                 #     # return JsonResponse(user.__dict__)
    #                 #     # options = UserOptions(user=user, display_name=user.username, email=email)
    #                 #     # options.save()
    #                 #     new_user = authenticate(username=user.username, password=password)
    #                 #     login(request, new_user)
    #                 #     # prnt('1111')
    #                 #     # if not options.userToken:
    #                 #     #     options.userToken = uuid4()
    #                 #     #     options.save()
    #                 #     # return 
    #                 #     # prnt(user.token)
    #                 #     # try:
    #                 #     #     u = User.objects.filter(username='Sozed')[0]
    #                 #     #     u.alert('New registered user', None, user.username)
    #                 #     #     # prnt('alert sent')
    #                 #     # except Exception as e:
    #                 #     #     prnt(str(e))
    #                 #     #     u = User.objects.filter(username='Sozed')[0]
    #                 #     #     u.alert('new user alert fail', None, str(e))
    #                 #     return redirect("/home")
    # else:
    #     prnt(userForm.errors)
    options = {'Login': '/login'}
    context = {
        'title': title,
        'cards': cards,
        "userForm": userForm,
        # "optionsForm": optionsForm,
        # 'view': view,
        'nav_bar': list(options.items()),
        'user_dict': get_signing_data(user_obj),
        # 'userOptions_dict': get_signature_data(options_obj),
        # 'feed_list':setlist,
        # 'topicList': topicList,
    }
    return render_view(request, context)

# not used
def login_options_view(request):
    from webauthn import (
        generate_authentication_options,
        verify_authentication_response,
        options_to_json,
        base64url_to_bytes,
    )
    from webauthn.helpers.structs import (
        PublicKeyCredentialDescriptor,
        UserVerificationRequirement,
    )

    # Simple Options
    simple_authentication_options = generate_authentication_options(rp_id="localhost")

    prnt("\n[Authentication Options - Simple]")
    prnt(options_to_json(simple_authentication_options))

    # # Complex Options
    # complex_authentication_options = generate_authentication_options(
    #     rp_id="localhost",
    #     challenge=b"1234567890",
    #     timeout=12000,
    #     allow_credentials=[PublicKeyCredentialDescriptor(id=b"1234567890")],
    #     user_verification=UserVerificationRequirement.REQUIRED,
    # )

    # prnt("\n[Authentication Options - Complex]")
    # prnt(options_to_json(complex_authentication_options))

    return JsonResponse(json.loads(options_to_json(simple_authentication_options)))

# step 2 of user login/signup
@csrf_exempt
def get_user_login_request_view(request):
    prnt('get_user login request')
    from utils.locked import get_signing_data, convert_to_dict
    if request.method == 'POST':
        received_json = request.POST
        prnt(received_json.get('display_name'))
        user = User.objects.filter(display_name=received_json.get('display_name')).first()
        if user:
            prnt(user.display_name)
            prnt('return 1')
            userData = get_signing_data(user, include_sig=True)
            try:
                sonet = json.dumps(convert_to_dict(Sonet.objects.first()))
            except:
                sonet = None
            prnt('return sign data', userData)
            return JsonResponse({'message' : 'User found', 'userData' : userData, 'upks' : [get_signing_data(upk_obj) for upk_obj in user.get_keys()], 'sonet' : sonet})
        else:
            user_id = hash_obj_id('User')
            upk_id = hash_obj_id('UserPubKey')
            dt = now_utc()
            display_name = received_json.get('display_name')
            prnt('new display_name',display_name)
            user = User(id=user_id, username=user_id, display_name=display_name)
            upk_obj = UserPubKey(id=upk_id, User_obj_id=user_id)
            upk_obj.initialize()
            # extra_data = {'User_obj':user_id}
            # prnt('user set up', user.__dict__)
            from blockchain.models import Node
            self_node = get_self_node()
            if not self_node:
                self_node = Node()
                self_node.initialize()
                # self_node.id = hash_obj_id(self_node)
            sonet = Sonet.objects.first()
            if not sonet:
                sonet = Sonet()
                sonet.initialize()
                if User.objects.all().count() == 0:
                    # user.id = super_id()
                    # user.username = super_id()
                    user.is_superuser = True
                    user.is_staff = True
                    # user.created_dt = sonet.created_dt
                    # upk_obj.User_obj_id = super_id()
            sonet = json.dumps(convert_to_dict(sonet))
            # prnt('extra_data',extra_data)
            prnt('return 2')
            return JsonResponse({'message' : 'User not found', 'userData' : get_signing_data(user), 'upkData' : get_signing_data(upk_obj), 'sonet' : sonet, 'nodeData':get_signing_data(self_node)})

# step 3 user login/signup
@csrf_exempt
def receive_user_login_view(request):
    prnt('receive_user22')
    err_code = '-'
    if request.method == 'POST':
        try:
            prnt()
            # prnt('request.POST',request.POST)
            # prnt('request.POST keys',request.POST.keys())
            # prnt('request.POST userData',request.POST.get('userData'))
            try:
                received_data = json.loads(request.body)
                userData = json.loads(received_data.get('userData'))
                try:
                    upkData = json.loads(received_data.get('upkData'))
                except:
                    upkData = {}
                try:
                    nodeData = json.loads(received_data.get('nodeData'))
                except:
                    nodeData = {}
                prnt('data',received_data)
            except Exception as e:
                prnt('err 535',str(e))
                userData = json.loads(request.POST.get('userData'))
                try:
                    upkData = json.loads(request.POST.get('upkData'))
                except:
                    upkData = {}
                try:
                    nodeData = json.loads(request.POST.get('nodeData'))
                except:
                    nodeData = {}


            # Access JSON values like:
            # userData = json.loads(received_data.get('userData'))
            # action = data.get('action')
            # prnt('userData',userData)
            # userData = json.loads(request.POST.get('userData'))
            prnt('received-userData',userData)
            # publicKey = request.POST.get('publicKey')
            # registeredPublicKey = request.POST.get('registered_public_key')
            prnt()
            prnt('isins',isinstance(userData, dict))
            userPublicKey = userData['publicKey']
            userSignature = userData['signature']
            prnt()
            prnt('pubkey', userPublicKey)
            prnt()
            prnt('sig', userSignature)
            user = User.objects.filter(display_name=userData['display_name']).first()
            if user:
                try:
                    prnt('user found', user)
                    if user.must_rename:
                        if User.objects.filter(display_name=userData['display_name']).exclude(id=userData['id']).count() > 0:
                            return JsonResponse({'message' : 'Username taken'})
                    x = get_signing_data(userData)
                    prnt()
                    prnt(x)
                    prnt('publicKey',userPublicKey)
                    upk = UserPubKey.objects.filter(User_obj=user, publicKey=userPublicKey, end_life_dt=None).first()
                    # prnt('upk',upk)
                    # upk2 = UserPubKey.objects.filter(User_obj=user, publicKey=publicKey).first()
                    # prnt('upk2',upk2)
                    # upkjeff = UserPubKey.objects.filter(User_obj__display_name='Jeff').first()
                    # prnt('upkjeff',upkjeff)
                    # if upkjeff:
                    #     prnt('upkjeff pubKey',upkjeff.publicKey)

                    if upk:
                        prnt('upk fouund:',upk)
                        is_valid = upk.verify(x, userSignature)
                        prnt('Login_is_valid', is_valid)
                        if is_valid:
                            if user.last_updated < string_to_dt(userData['last_updated']):
                                user, good = sync_and_share_object(user, userData)
                                prnt('user-good',good)
                            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                            prnt('user logged in')
                            response = JsonResponse({'message' : 'Valid Username and Password', 'userData' : x, 'upk' : get_signing_data(upk)})
                            # response.set_cookie(key='userData', value=json.dumps(x), expires=datetime.datetime.today()+datetime.timedelta(days=3650))
                            return response
                        else:
                            return JsonResponse({'message' : 'Verification failed'})
                    else:
                        return JsonResponse({'message' : 'Invalid Password'})
                except Exception as e:
                        prnt(str(e))
                        return JsonResponse({'message' : f'A Problem Occured: {e}', 'err':str(e)})
            else:
                try:
                    err_code = 'A'
                    prnt('1')
                    validator_upk = UserPubKey()
                    
                    prnt('Intial userData',userData)
                    # # upkData = json.loads(request.POST.get('upkData'))
                    # upkData = json.loads(received_data.get('upkData'))
                    prnt('upkData',upkData)
                    upkSignature = upkData['signature']
                    prnt('upkSignature',upkSignature)
                    # user and upk must exist before attempts to sync
                    err_code = 'B'
                    if validator_upk.verify(get_signing_data(userData), userSignature, userPublicKey):
                        prnt('L1')
                        if validator_upk.verify(get_signing_data(upkData), upkSignature, userPublicKey):
                            prnt('L2')

                            user = User()
                            prnt('create user')
                            for key, value in userData.items():
                                if value != 'None':
                                    prnt(key, value)
                                    if '_array2' in str(key):
                                        prnt('TARGET',key, ast.literal_eval(value))
                                        setattr(user, key, ast.literal_eval(value))
                                    else:
                                        setattr(user, key, value)
                            prnt('save user first time')
                            err_code = 'C'
                            user.save(share=False, is_new=True)
                            try:
                                prnt('new user', user)
                            except Exception as e:
                                prnt(str(e))
                            prnt()
                            prnt('create 111')

                            err_code = 'D'
                            upk = UserPubKey()
                            prnt('create upk')
                            for key, value in upkData.items():
                                if value != 'None':
                                    # prnt(key,value)
                                    if str(key) == 'User_obj':
                                        setattr(upk, 'User_obj_id', value)
                                    else:
                                        setattr(upk, key, value)
                            prnt('save upk')
                            # prnt(model_to_dict(upk))
                            upk.save(share=False, is_new=True)
                            prnt('savedupk:',UserPubKey.objects.filter(id=upk.id).first())
                            prnt('create 222')
                            err_code = 'E'


                    err_code = 1
                    proceed_to_login = False
                    if upk and upk.verify(get_signing_data(upkData), upkSignature):
                    # if is_valid:
                        err_code = 2
                        if upk.verify(get_signing_data(userData), userSignature):
                        # if is_valid:
                            err_code = 3
                            # is_valid = upk.verify(get_signing_data(walletData), walletSignature)
                            # if is_valid:
                            try:
                                prnt('try')
                                user = get_or_create_model(userData['object_type'], id=userData['id'])
                                prnt('u2')
                                err_code = 4
                                # upk.User_obj = user
                                user, good = sync_and_share_object(user, userData)
                                prnt('done user22',user)
                                from utils.locked import convert_to_dict
                                prnt('uc2d:',convert_to_dict(user))
                                # user.slug = user.slugger()
                                err_code = 5
                                user.save()
                                prnt('user-good',good)
                                # prnt('new user data', get_signing_data(user))
                                prnt()
                                err_code = 6
                                upk = get_or_create_model(upkData['object_type'], id=upkData['id'])
                                # upk.User_obj = user
                                err_code = 7
                                upk, good = sync_and_share_object(upk, upkData)
                                prnt('upk-good',good)
                                err_code = 8

                                # user.create_wallet()

                                # wallet = get_or_create_model(walletData['object_type'], id=walletData['id'])
                                # # wallet.User_obj = user
                                # wallet, good = sync_and_share_object(wallet, walletData)
                                # prnt('wallet-good',good)
                                proceed_to_login = True
                            except Exception as e:
                                prnt('fail3726',str(e),'\n')
                                err_code = str(err_code) + '/' + str(e)


                            # prnt()
                            err_code = 9
                            prnt('\n\n\n\n')
                            prnt('newU', user)
                            new_user_valid = upk.verify(get_signing_data(user), userSignature)
                            prnt('new_user_valid',new_user_valid)
                            err_code = 10
                            node = None
                            from utils.locked import super_id
                            if super_id(user.id):
                                err_code = 11
                                user.assess_super_status()
                                prnt('user.is_superuser',user.is_superuser)
                                # nodeData = None
                                try:
                                    prnt('trynode1')
                                    # nodeData = json.loads(received_data.get('nodeData'))
                                    # nodeData = json.loads(request.POST.get('nodeData'))
                                    prnt('nodeData',nodeData)
                                    from blockchain.models import Node
                                    if Node.objects.first():
                                        prnt('Node.objects.first()',Node.objects.first())
                                        nodeData = None
                                except:
                                    prnt('falitrynode1')
                                    nodeData = None
                                if nodeData and user.is_superuser:
                                    prnt('step2', nodeData)
                                    if validator_upk.verify(get_signing_data(nodeData), nodeData['signature'], userPublicKey):
                                        prnt('step2a')
                                        node = Node()
                                        for key, value in nodeData.items():
                                            if value != 'None':
                                                # prnt(key,value)
                                                if str(key) == 'User_obj':
                                                    setattr(node, 'User_obj_id', value)
                                                else:
                                                    setattr(node, key, value)
                                        prnt('save node')
                                        # prnt(model_to_dict(upk))
                                        node.save()
                                        prnt('create 333')
                                        err_code = 'F'
                                        user.nodeCreatorId = node.id
                                        user.save()
                            else:
                                prnt('else1')
                                if not node:
                                    node = get_self_node()
                                user.nodeCreatorId = node.id
                                user.save()

                            if not new_user_valid:
                                err_code = 12
                                proceed_to_login = False
                            prnt('step3')
                            # prnt('signingdata',get_signing_data(userData))
                            # prnt()
                            # prnt('signinguser', get_signing_data(user))
                    # prnt('is valid', is_valid)
                    if proceed_to_login:
                        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                        prnt('user logged in')
                        sonet_obj = Sonet.objects.first()
                        if not sonet_obj:
                            sonet_obj = Sonet()
                            sonet_obj.initialize()
                        sonet = get_signing_data(sonet_obj)
                        return JsonResponse({'message' : 'User Created', 'userData' : get_signing_data(user), 'upk' : get_signing_data(upk), 'sonet' : sonet})
                    else:
                        try:
                            from blockchain.models import Blockchain
                            chains = Blockchain.objects.filter(genesisId=user.id)
                            for w in chains:
                                w.delete()
                        except:
                            pass
                        try:
                            prnt('deleting user...')
                            # prnt(get_signing_data(user))
                            user.delete()
                        except:
                            pass
                        try:
                            upk.delete()
                        except:
                            pass
                        prnt('new user data deleted',f'fail2:{err_code}')
                        return JsonResponse({'message' : f'There was a problem creating this user, err:{err_code}', 'error':f'fail2:{err_code}'})
                except Exception as e:
                    prnt('fail94578', str(e), 'err:',err_code)
                    try:
                        from blockchain.models import Blockchain
                        chains = Blockchain.objects.filter(genesisId=user.id)
                        for w in chains:
                            w.delete()
                    except:
                        pass
                    try:
                        user.delete()
                    except:
                        pass
                    try:
                        upk.delete()
                    except:
                        pass

                    return JsonResponse({'message' : f'There was a problem creating this user, err:{err_code} - {e}', 'error': f'fail1: {err_code}-{str(e)}'})
        except Exception as e:
            prnt('receive login fail 3467 err_code:',err_code,str(e))
            return JsonResponse({'message' : f'error: {e}'})
    return JsonResponse({'message' : 'success'})


def username_avail_view(request):
    # style = request.GET.get('style', 'index')
    # sort = request.GET.get('sort', 'recent')
    # view = request.GET.get('view', '')
    # sort = request.GET.get('sort', 'Newest')

    username = request.GET.get('username', '').strip()
    prnt(username)
    if len(username) >= 4:
        exists = User.objects.filter(display_name__iexact=username).exists()
    else:
        exists = True
    prnt(exists)
    return JsonResponse({'available': not exists})

    # keyword = request.GET.get('keyword', keyword)
    # keyword = keyword.lower()
    # response = User.objects.filter(display_name__iexact=keyword).first()
    # return render(request, "utils/dummy.html", {"result": response})
    
    # page = request.GET.get('page', 1)
    # search = request.POST.get('post_type', '')
    # autoComplete = request.GET.get('search')
    # follow = request.GET.get('follow', '')
    # cards = 'home_list'
    # ordering = get_sort_order(sort)
    # title = 'Search: %s' %(search)    
    # # province, region = get_region(request)
    # user_data, user = get_user_data(request)
    # country, provState, county, city = get_regions(request, None, user)
    # chambers, current_chamber, all_chambers, gov_levels = get_chambers(request, country, provState, county, city)
    # options = {'Chamber: %s' %(Chamber): 'Chamber'}
    # nav_options = [nav_item('button', f'Chamber:{Chamber}', 'subNavWidget("chamberForm")')]
    searchform = SearchForm(initial={'post_type': search})
    subtitle = ''
    if follow and follow != 'following' and follow != 'follow':
        # if request.user.is_authenticated:
        #     user = request.user
        # else:
        #     try:
        #         userToken = request.COOKIES['userToken']
        #         user = User.objects.filter(userToken=userToken)[0]
        #     except:
        #         pass
        if user:
            fList = user.get_follow_topics()
            topic = follow
            if topic in fList:
                fList.remove(topic)
                response = 'Unfollow "%s"' %(topic)
                user = set_keywords(user, 'remove', topic)
            elif topic not in fList:
                fList.append(topic)
                response = 'Following "%s"' %(topic)
                user = set_keywords(user, 'add', topic)
            user.set_follow_topics(fList)
            user.save()
        else:
            response = 'Please login'
        return render(request, "utils/dummy.html", {"result": response})
    if keyword:
        title = 'Search: %s' %(keyword)
        # options['follow'] = '%s' %(keyword)
        nav_options.append(nav_item('button', 'follow', f'react("follow2", "{keyword}")'))
        posts = Post.objects.filter(keyword_array__icontains=keyword).exclude(date_time=None).order_by(ordering,'-date_time')
        if posts.count() == 0:
            posts = Archive.objects.filter(keyword_array__icontains=keyword).exclude(date_time=None).order_by(ordering,'-date_time')
        if posts.count() == 1:
            response = redirect(posts[0].get_absolute_url())
            return response
    elif autoComplete:
        keyphrases = Keyphrase.objects.filter(Chamber__iexact__in=Chambers).filter(key__icontains=autoComplete)[:500]
        # if Chamber == 'All':
        # else:
        #     keyphrases = Keyphrase.objects.filter(Chamber__iexact=Chamber).filter(text__icontains=autoComplete)[:500]

        # if Chamber == 'All':
        #     if 
        #     keyphrases = Keyphrase.objects.filter(text__icontains=autoComplete)[:500]
        #     # prnt(keyphrases)
        # elif Chamber == 'House':
        #     keyphrases = Keyphrase.objects.filter(Chamber__iexact=Chamber).filter(text__icontains=autoComplete)[:500]
        # elif Chamber == 'Senate':
        #     keyphrases = Keyphrase.objects.filter(organization='Senate').filter(text__icontains=autoComplete)[:500]
        # elif Chamber == 'Assembly':
        #     # org = get_province_name
        #     keyphrases = Keyphrase.objects.filter(organization='%s-Assembly'%(region)).filter(text__icontains=autoComplete)[:500]
        data = []
        for k in keyphrases:
            if k.key not in data:
                data.append(k.key)
        return JsonResponse({'status':200, 'data':data})
    else:
        posts = {}
    try:
        setlist = paginate(posts, page, request)
    except:
        setlist = []
    # useractions = get_useractions(request, setlist) 
    try:
        isApp = request.COOKIES['fcmDeviceId']
    except:
        isApp = None 
    # my_rep = getMyRepVotes(request, setlist) 
    # options = {'Chamber: %s' %(Chamber): 'Chamber', 'Page: %s' %(page): '?page=1', 'Sort: %s'%(sort): sort, 'Search': 'search', 'Date': 'date'}
    nav_options = [nav_item('button', f'Chamber:{Chamber}', 'subNavWidget', 'chamberForm'), 
                   nav_item('button', 'Page: %s' %(page), 'subNavWidget', 'pageForm'),
            # nav_item('link', 'Page: %s' %(page), '?view=%s&page=' %(view)), 
            nav_item('button', 'Sort: %s'%(sort), 'subNavWidget', 'sortForm'), 
            # nav_item('link', 'Current', '?view=Current'), 
            # nav_item('link', 'Upcoming', '?view=Upcoming'),
            nav_item('button', 'Search', 'subNavWidget', 'searchForm'), 
            nav_item('button', 'Date', 'subNavWidget', 'datePickerForm')]
    context = {
        'isApp': isApp,
        'title': title,
        'subtitle': subtitle,
        'nav_bar': nav_options,
        'sort': sort,
        'sortOptions': ['OLdest','Newest','Loudest','Random'],
        'keyword': keyword,
        'view': view,
        # 'region': region,
        'searchForm': searchform,
        'cards': cards,
        'feed_list':setlist,
        'useractions': get_useractions(user, setlist),
        # 'updates': get_updates(setlist),
        'myRepVotes': getMyRepVotes(user, setlist),
        'topicList': [keyword],
        # 'myRepVotes': my_rep,
        # 'country': Country.objects.all()[0],
    }
    return render_view(request, context, country=country)


# not currently used
def login_verify_view(request):
    prnt('login verify')
    import hashlib

    # from webauthn import (
    #     generate_authentication_options,
    #     verify_authentication_response,
    #     options_to_json,
    #     base64url_to_bytes,
    # )
    # from webauthn.helpers.structs import (
    #     PublicKeyCredentialDescriptor,
    #     UserVerificationRequirement,
    # )
    # received_json = json.loads(request.POST['content'])
    # prnt(received_json)
    # # Authentication Response Verification
    # authentication_verification = verify_authentication_response(
    #     # Demonstrating the ability to handle a stringified JSON version of the WebAuthn response
    #     credential=received_json,
    #     expected_challenge=base64url_to_bytes(
    #         "iPmAi1Pp1XL6oAgq3PWZtZPnZa1zFUDoGbaQ0_KvVG1lF2s3Rt_3o4uSzccy0tmcTIpTTT4BU1T-I4maavndjQ"
    #     ),
    #     expected_rp_id="localhost",
    #     expected_origin="http://localhost:5000",
    #     # credential_public_key=base64url_to_bytes(
    #     #     "pAEDAzkBACBZAQDfV20epzvQP-HtcdDpX-cGzdOxy73WQEvsU7Dnr9UWJophEfpngouvgnRLXaEUn_d8HGkp_HIx8rrpkx4BVs6X_B6ZjhLlezjIdJbLbVeb92BaEsmNn1HW2N9Xj2QM8cH-yx28_vCjf82ahQ9gyAr552Bn96G22n8jqFRQKdVpO-f-bvpvaP3IQ9F5LCX7CUaxptgbog1SFO6FI6ob5SlVVB00lVXsaYg8cIDZxCkkENkGiFPgwEaZ7995SCbiyCpUJbMqToLMgojPkAhWeyktu7TlK6UBWdJMHc3FPAIs0lH_2_2hKS-mGI1uZAFVAfW1X-mzKL0czUm2P1UlUox7IUMBAAE"
    #     # ),
    #     credential_current_sign_count=0,
    #     require_user_verification=True,
    # )
    # prnt("\n[Authentication Verification]")
    # prnt(authentication_verification)
    # assert authentication_verification.new_sign_count == 1
    # # return JsonResponse(json.loads(options_to_json(authentication_verification)))

    prnt()
    import base64
    # prnt(request.POST)
    prnt('1')
    # elem = base64.b64decode(request.POST)
    # prnt(request.body.decode())
    # prnt(elem)
    received_json = request.POST
    prnt(received_json)
    # for i in received_json:
    #     prnt(i)
    #     prnt(received_json[i])
    prnt()
    prnt(received_json['publicKeyHex'])
    prnt()
    prnt('td', str(received_json['transactionData']))
    prnt()
    # prnt('privKey received',received_json['privateKey'])
    prnt()
    prnt(str(received_json['signature']))
    # prnt()
    # prnt(received_json['r'])
    # prnt()
    # prnt(received_json['s'])
    # from ethereum.utils import ecrecover, pub_to_address, to_buffer, to_checksum_address, from_rpc_sig
    from ecdsa import SECP256k1, VerifyingKey, BadSignatureError, util

    # signed_tx_data = request.POST.get('signedData')
    # prnt(signed_tx_data)
    # privateKey = request.POST.get('privateKey')
    publicKey = request.POST.get('publicKeyHex')
    transaction_data = request.POST.get('transactionData')
    signature = request.POST.get('signature')
    # r = request.POST.get('r')
    # s = request.POST.get('s')
    # signature = ['48', '68', '2', '32', '75', '213', '151', '71', '233', '42', '173', '36', '183', '158', '166', '10', '106', '120', '212', '39', '50', '167', '38', '155', '126', '181', '25', '253', '206', '34', '83', '133', '14', '214', '31', '255', '2', '32', '34', '43', '162', '192', '13', '128', '84', '45', '29', '73', '173', '198', '201', '81', '84', '42', '206', '249', '189', '189', '198', '13', '167', '13', '144', '63', '177', '244', '12', '6', '101', '139']
    # signature = ''.join(signature)
    # prnt(signature)
    prnt()


    from ecdsa import SECP256k1, VerifyingKey

    # Received signature and public key from JavaScript
    signature_hex = signature
    public_key_hex = publicKey

    # # Decode public key
    # public_key = VerifyingKey.from_string(bytes.fromhex(publicKey), curve=SECP256k1)

    # # Prepare data (replace with the same data used in JavaScript)
    data = "Transaction data"
    # # hash = bytes.fromhex(require('crypto').createHash('sha256').update(data).digest('hex'))
    message = b"testmessage"
    prnt(message)
    # sig = r+s
    # # Verification
    # try:
    #     if public_key.verify(bytes.fromhex(sig), message):
    #         prnt("Signature is valid!")
    #     else:
    #         prnt("Signature is invalid!")
    # except Exception as e:
    #     prnt(str(e)) 
    #     prnt("Verification failed!")
    # public_key_hex = '04f8ccf508990ceef9e5b84f5aeb9fee1739d3d3b140fc05e5b2ff58524c660ba27f654ed36fe7dd9923a1ffaf5caa774c2e9fd18ffb486432f44914c22c29eccf'
    # signature_hex = '3044022010f92d4771aac187375265167f43854d510428a131124df798b406a5dcc7eab5022029bbadf9aa6b4741d7fed01999121fe34ad8b2216f7200d953904bbd271d84e0'

    # # Parse the public key
    # vk = VerifyingKey.from_string(bytes.fromhex(public_key_hex), curve=SECP256k1)

    # # Parse the signature
    # r, s = int(signature_hex[:64], 16), int(signature_hex[64:], 16)
    # prnt(r)
    # prnt(s)
    # # Verify the signature
    # if vk.verify(bytes.fromhex(signature_hex), message, hashfunc=hashlib.sha256, sigdecode="raw"):
    #     prnt("Signature is valid!")
    # else:
    #     prnt("Signature is invalid!")
    

    # from ecdsa import SECP256k1, VerifyingKey

    # vk = VerifyingKey.from_string(bytes.fromhex(public_key_hex), curve=SECP256k1)
    # prnt(vk.verify(bytes.fromhex(signature), message))
    # import binascii                         #you'll need this module for this one
    # ecdh = ec.keyFromSecret(password)       #//password is your seed phrase here
    # hex_string = binascii.unhexlify(signature);  #//signature should be hexadecimal string containing r value, s value and recovery id
    # binint = int.from_bytes(hex_string, 'big')   #this will convert the byte string into a big integer object


    # ecdh = ec.keyFromSecret(password)   #password is your seed phrase here
    # verified = ecdh.verify(binint, message);    
    # # //data can be a string or number and signature is hexadecimal string containing r value, s value and recovery id


    # # Replace with the retrieved signature (in bytes)
    # signature_bytes = str.encode(signature)

    # # Replace with the retrieved public key (in DER format)
    # public_key_der = str.encode(publicKey)

    # # Decode the public key from DER format
    # # curve = ecdsa.curves.SECP256k1  # Assuming secp256k1 curve
    # # public_key = curve.decode_point(public_key_der)



    # from asn1crypto import DER

    # # Replace with the retrieved public key in DER format
    # # public_key_der = b"your_public_key_in_der_format"

    # # Decode the DER-encoded public key
    # decoded_data = DER().decode(public_key_der)

    # # Extract the X and Y coordinates (assuming uncompressed format)
    # x = decoded_data[1].as_integer()
    # y = decoded_data[2].as_integer()

    # # Create a public key object suitable for ecdsa
    # curve = ecdsa.curves.SECP256k1  # Assuming secp256k1 curve
    # public_key = ecdsa.Public_key(curve, x, y)

    # # ... (Rest of the verification code using the public_key object)




    # Hash the message (ensure it matches the hashing algorithm used in JavaScript)
    message = b"testmessage"  # Replace with the actual message
    hash_func = hashlib.sha256  # Assuming SHA-256 was used
    message_hash = hash_func(message).digest()

    # # Verify the signature
    # try:
    #     ecdsa.VerifyingKey.from_public_point(public_key, curve=curve).verify(signature_bytes, message)
    #     prnt("Signature is valid")
    # except ecdsa.BadSignatureError:
    #     prnt("Signature is invalid")
    # except Exception as e:
    #     prnt(str(e))






    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature, decode_dss_signature
    from cryptography.hazmat.primitives.serialization import load_der_public_key
    from cryptography.hazmat.primitives import hashes
    from cryptography.exceptions import InvalidSignature
    import base64
    import json



    # Uncompressed public key (hexadecimal string)
    # uncompressed_public_key_hex = "04f8ccf508990ceef9e5b84f5aeb9fee1739d3d3b140fc05e5b2ff58524c660ba27f654ed36fe7dd9923a1ffaf5caa774c2e9fd18ffb486432f44914c22c29eccf"

    # Decode the uncompressed public key from hexadecimal
    # uncompressed_public_key_bytes = bytes.fromhex(publicKey)

    # # Load the DER-encoded public key
    # publicKey = serialization.load_der_public_key(uncompressed_public_key_bytes, backend=default_backend())

    # Construct an EllipticCurvePublicKey object directly
    # public_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), uncompressed_public_key_bytes)

    # der_public_key = bytes.fromhex('04f8ccf508990ceef9e5b84f5aeb9fee1739d3d3b140fc05e5b2ff58524c660ba27f654ed36fe7dd9923a1ffaf5caa774c2e9fd18ffb486432f44914c22c29eccf')
    # publicKey = base64.b64decode('027b83ad6afb1209f3c82ebeb08c0c5fa9bf6724548506f2fb4f991e2287a77090')
    # publicKey = base64.b64decode('''MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC+6gvHdCUCjnc4hSMwbdIIspk469pVAzjjb8tDJsCH/QpiK9vXe4nDZ7p9kiw2ACw0fkWaPnApKBwXNB9Nd9Sf+XFtcIzdqKKBcAqZZCu2pA729amNRug9DoZdkstaBG+VfTxXhdzQRSTxxqJQWgdV8ejKkt4D1M6pAiTkAyD0eQIDAQAB''')
    # data = {
    # "data_1":"The quick brown fox",
    # "data_2":"jumps over the lazy dog"
    # }
    # data = "jumps over the lazy dog1111"
    # prnt('d', data)
    prnt('td', transaction_data)
    data = transaction_data


    
    # signature = base64.b64decode(signature)

    # (r, s) = decode_dss_signature(signature)
    # prnt(r)
    # prnt(s)
    # signatureP1363 = r.to_bytes(32, byteorder='big') + s.to_bytes(32, byteorder='big')
    # prnt(base64.b64encode(signatureP1363).decode('utf-8'))

    # publicKey = load_der_public_key(der_public_key, default_backend())
    signature_bytes = bytes.fromhex(signature)
    prnt(signature_bytes.hex())
    public_key_bytes = bytes.fromhex(publicKey)
    public_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), public_key_bytes)
    prnt('pubkey loaded', publicKey)
    # data = "testmessage"
    try:
        public_key.verify(signature_bytes, data.encode('utf-8'), ec.ECDSA(hashes.SHA256()))
        prnt("Signature is valid YAY IT WORKED!!!.")
    except InvalidSignature:
        prnt("Invalid signature.")
    except Exception as e:
        prnt(str(e))
    

    # r = int.from_bytes(r.encode('utf-8'), byteorder='big')
    # s = int.from_bytes(s.encode('utf-8'), byteorder='big')
    # prnt(r)
    # prnt(s)

    # try:
    #     publicKey.verify(
    #         encode_dss_signature(r, s),
    #         json.dumps(data, separators=(',', ':')).encode('utf-8'),
    #         ec.ECDSA(hashes.SHA256())    
    #     )
    #     prnt("verification succeeded")
    # except InvalidSignature:
    #     prnt("verification failed")
    # except Exception as e:
    #     prnt(str(e))



# not used
def login_view_old(request):
    if request.user.is_authenticated:
        return redirect("/home")
    style = request.GET.get('style', 'index')
    title = "Login"
    cards = 'login'
    form = UserLoginForm(request.POST or None)
    # prnt(form)
    if form.is_valid():
        # prnt('isvalid')
        username = form.cleaned_data.get("username")
        password = form.cleaned_data.get('password')
        # prnt(username)
        user = authenticate(username=username, password=password)
        # prnt(user)
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        # prnt('logged in')
        try:
            userToken = request.COOKIES['userToken']
        except:
            userToken = None
        if userToken and userToken != user.userToken:
            try:
                anon_user = User.objects.filter(userToken=userToken, anon=True)[0]
                reactions = Reaction.objects.filter(user=anon_user)
                for r in reactions:
                    r.user = user
                    r.save()
                if anon_user.keywords:
                    if not user.keywords:
                        user.keywords = []
                    for k in anon_user.keywords:
                        user.keywords.append(k)
                    user.save()
                # anon_user.delete()
            except:
                pass
        if not user.userToken:
            rand_token = uuid4()
            user.userToken = rand_token
            user.save()
        # prnt(user.token)
        try:    
            fcmDeviceId = request.COOKIES['fcmDeviceId']
            # prnt(fcmDeviceId)
            devices = FCMDevice.objects.filter(user=request.user, registration_id=fcmDeviceId)
            for d in devices:
                d.send_message(Message(data={"signin" : "True", 'token' : user.appToken}))
            return redirect("/home?appToken=%s&fcmDeviceId=%s" %(user.appToken, fcmDeviceId))
        except Exception as e:
            prnt(str(e))
            
            # if next:
            #     return redirect(next)
            return redirect("/home")
    else:
        prnt(form.errors)
    options = {'Sign Up': '/signup'}
    context = {
        'title': title,
        'cards': cards,
        "form": form,
        # 'view': view,
        'nav_bar': list(options.items()),
        # 'feed_list':setlist,
        # 'topicList': topicList,
    }
    return render_view(request, context)


def logout_view(request):
    # prnt('logout')
    # prnt(request.user)
    try:    
        fcmDeviceId = request.COOKIES['fcmDeviceId']
        prnt(fcmDeviceId)
        # shouuld use CustomFCM
        devices = FCMDevice.objects.filter(user=request.user, registration_id=fcmDeviceId)
        for d in devices:
            # d.send_message(Message(notification=Notification(title=request.user.username, body="body")))
            d.send_message(Message(data={"logout" : "True"}))
            d.active = False
            d.save()
    except Exception as e:
        prnt('error438532', str(e))
    # try:
    #     userToken = request.COOKIES['userToken']
    # except Exception as e:
    #     userToken = None
    logout(request)
    context = {
        "user": None,

    }
    response = render(request, "index.html", context)
    # response = redirect("/")
    response.set_cookie(key='appToken', value=None)
    response.set_cookie(key='userData', value=None)
    # response.set_cookie(key='userToken', value=userToken)
    return response

def get_index_view(request):
    prnt('get index view')
    if request.user.is_authenticated:
        user = request.user
    else:
        user = None
    context = {
        "user": user,
    }
    return render(request, "index.html", context)

def get_country_modal_view(request):
    prnt('country modal view')
    user_data, user = get_user_data(request)
    if not user:

        user_id = hash_obj_id('User')
        user_obj = User(id=user_id, username=user_id)
        context = {
            'title': 'Login/Signup',
            'user_dict': get_signing_data(user_obj),
        }
        return render(request, "forms/login-signup.html", context)
    else:
        return render(request, "forms/region_modal1.html")

def get_region_modal_view(request, country):
    prnt('region modal view', country)
    return render(request, "forms/region_modal2.html", {'country': country})

def run_region_modal_view(request):
    prnt('run region modal')
    if request.method == 'POST':
        # from utils.models import list_all_scrapers
        u = request.user
        # do not save data to user profile, must be sent to user for signature then returned
        # u = User()
        # fields = user._meta.fields
        # for f in fields:
        #     setattr(u, f.name, getattr(user, f.name))
        # received_json = request.POST
        # prnt(received_json)
        # newPrivateKey = request.POST.get('new_private_key')
        address = request.POST.get('address')
        city = request.POST.get('city')
        state = request.POST.get('state')
        zip_code = request.POST.get('zip_code')
        country = request.POST.get('country')
        # regionSetDate = request.POST.get('regionSetDate')
        # signature = request.POST.get('setDateSig')
        # user_id = request.POST.get('userId')
        # prnt('user_id', user_id)
        # prnt('sig', signature)
        # try:
        #     user = User.objects.filter(id=user_id)[0]
        #     prnt(user)
        #     pubKeys = UserPubKey.objects.filter(User=user)
        #     prnt(pubKeys)
        #     for pubKey in pubKeys:
        #         prnt(pubKey.publicKey)
        #         is_valid = pubKey.verify(signature, regionSetDate)
        #         if is_valid:
        #             break
        # except Exception as e:
        #     prnt(str(e))
        #     is_valid = False
        prnt('start hree')
        prnt('country',country)



        all_files = list_all_scrapers()
        prnt(all_files)

        scripts = {}
        for file in all_files:
            try:
                a = file.find('/scrapers/')+len('/scrapers/')
                x = file[a:]
                words = x.split('/')
                region = words[-2]
                prnt('regions:',region)
                if region.lower() == country.lower():

                    txt = x.replace('/', '.').replace('.py','')
                    scripts[txt] = []
                    import importlib
                    scraperScripts = importlib.import_module(txt) 
                    approved_models = scraperScripts.approved_models
                    # for f, models in approved_models.items():
                    #     scripts[txt].append({txt:f})

                    cmd = getattr(scraperScripts, 'get_user_region')
                    returnData, shareData = cmd(address=address, city=city, state=state, zip_code=zip_code)
                    return JsonResponse({'message': 'success', 'result':returnData})
            except Exception as e:
                prnt(str(e))
                return JsonResponse({'message' : 'Failed to set region', 'error':str(e)})
                # pass
        return JsonResponse({'message' : 'Failed to set region', 'error':'Country not found'})


        # if country == 'canada':
        #     try:
        #         from scrapers.canada.federal import get_user_region
        #         if len(address) <= 7:
        #             prnt('1')
        #             address = address.upper().replace(' ', '')
        #             # u.postal_code = address
        #             # u = u.clear_region()
        #             url = 'https://represent.opennorth.ca/postcodes/%s/' %(address)
        #             # prnt('get user data')
        #             result = get_user_region(u, url)
        #             # u.region_set_date = datetime.datetime.now()
        #         else:
        #             prnt('2')
        #             url = 'http://dev.virtualearth.net/REST/v1/Locations/CA/%s?output=xml&key=AvYxl5kFcs1G1CKjpXM8atABzd_8Wb8shd8OJ2cG3-MtQjOa6Bg7rIOthHLGbDgA' %(address)
        #             r = requests.get(url)
        #             soup = BeautifulSoup(r.content, 'lxml')
        #             latitude = soup.find('latitude').text
        #             longitude = soup.find('longitude').text
        #             url = 'https://represent.opennorth.ca/boundaries/?contains=%s,%s' %(latitude, longitude)
        #             prnt(url)
        #             # u = u.clear_region()
        #             result1 = get_user_region(u, url)
        #             url = 'https://represent.opennorth.ca/representatives/?point=%s,%s' %(latitude, longitude)
        #             prnt(url)
        #             # prnt('----------------------------------------------------')
        #             result2 = get_user_region(u, url)
        #             result = {**result1, **result2}
        #             # result = {**result1, **result2}
        #             # u.address = address
        #             # u.region_set_date = datetime.datetime.now()
        #         # if is_valid:
        #         #     # Mon, 12 Sep 2022 18:15:18 GMT
        #         #     setDate = datetime.datetime.strptime(regionSetDate, '%a, %d %b %Y %H:%M:%S %Z')
        #         #     # user.region_set_date = setDate
        #         #     # user.save()
        #         #     result['regionSetDate'] = setDate
        #         # prnt(u.__dict__)
        #         # prnt()
        #         # u.last_updated = datetime.datetime.now()
        #         x = get_user_sending_data(u)
        #         # prnt()
        #         prnt('check here 1')
        #         prnt(x)
        #         # prnt()
        #         # dump = json.dump(x)
        #         # prnt(dump)
        #         return JsonResponse({'message': 'success', "userData": x, 'result':result})
        #     except Exception as e:
        #         prnt(str(e))
        #         return JsonResponse({'message' : 'Failed to set region'})

@csrf_exempt
def set_user_data_view(request):
    prnt('set user data view')
    if request.method == 'POST':
        # received_json = request.POST
        # prnt(received_json)
        # prnt()
        userData = request.POST.get('userData')
        prnt('received', userData)
        prnt()
        # prnt('siging_data', str(get_signing_data(userData)))
        prnt()
        # prnt('siging_local', str(get_signing_data(request.user)))
        # userData = json.load(x)
        
        user = request.user
        # data is verified during sync
        user, synced = sync_and_share_object(user, userData)
        prnt('synced',synced)
        if synced:
            return JsonResponse({'message':'success'})
        else:
            return JsonResponse({'message':'Failed to sync'})
    return JsonResponse({'message':'Failed verification'})

#not used
def redirect_to_social_auth_view(request):
    fcmDeviceId = request.GET.get('fcmDeviceId', '')
    if fcmDeviceId:
        response = redirect("/accounts/google/login")
        prnt('writing cookie')
        response.set_cookie(key='fcmDeviceId', value=fcmDeviceId, expires=datetime.datetime.today()+datetime.timedelta(days=3650))
        # response.set_cookie(key='sotoken', value=token)
        return response
    else:
        return redirect("/accounts/google/login")
#not used
def redirect_from_social_auth_view(request):
    # try:
    #     u = User.objects.filter(socialAuth=request.user)[0]
    # except:
    #     from random_username.generate import generate_username
    #     rand_username = generate_username(1)[0] 
    #     u = User(socialAuth=request.user, username=rand_username)
    #     u.set_password(uuid4())
    #     u.slugger()
    #     u.save()
    # user = authenticate(username=u.username, password=u.password)
    # login(request, user)
    user = request.user
    if not user.slug:
        user.slugger()
        user.save()
    try:
        userToken = request.COOKIES['userToken']
    except:
        userToken = None
    if userToken and userToken != user.userToken:
        try:
            anon_user = User.objects.filter(userToken=userToken, anon=True)[0]
            reactions = Reaction.objects.filter(user=anon_user)
            for r in reactions:
                r.user = user
                r.save()
            if anon_user.keywords:
                if not user.keywords:
                    user.keywords = []
                for k in anon_user.keywords:
                    user.keywords.append(k)
                user.save()
            # anon_user.delete()
        except:
            pass
    if not user.userToken:
        rand_token = uuid4()
        user.userToken = rand_token
        user.save()
    try:
        u = User.objects.filter(username='d704bb87a7444b0ab304fd1566ee7aba')[0]
        u.alert('New registered user', None, user.username)
    except:
        pass
    try:    
        fcmDeviceId = request.COOKIES['fcmDeviceId']
        if fcmDeviceId:
            prnt(fcmDeviceId)
            devices = FCMDevice.objects.filter(user=request.user, registration_id=fcmDeviceId)
            for d in devices:
                d.send_message(Message(data={"signin" : "True", 'token' : user.appToken}))
            return redirect("/home?appToken=%s&fcmDeviceId=%s" %(user.appToken, fcmDeviceId))
        else:
            return redirect("/home")
    except Exception as e:
        return redirect("/home")

# not used
def api_login_view(request):
    try:
        username = request.GET.get("name")
        user = User.objects.get(username=username)
        password = request.GET.get('pass')
        # prnt(username)
        user = authenticate(username=username, password=password)
        # prnt(user)
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        # prnt('logged in')
        try:
            userToken = request.COOKIES['userToken']
        except:
            userToken = None
        if userToken and userToken != user.userToken:
            try:
                anon_user = User.objects.filter(userToken=userToken, anon=True)[0]
                reactions = Reaction.objects.filter(user=anon_user)
                for r in reactions:
                    r.user = user
                    r.save()
                # anon_user.delete()
            except:
                pass
        if not user.userToken:
            rand_token = uuid4()
            user.userToken = rand_token
            user.save()
        if not user.appToken:
            rand_token = uuid4()
            user.appToken = rand_token
            user.save()
        return render(request, "utils/dummy.html", {"result": user.appToken})
        
    except Exception as e:
        prnt(str(e))
        return render(request, "utils/dummy.html", {"result": 'Fail'})
# not used
def api_create_user_view(request):
    try:
        username = request.GET.get('name')
        password = request.GET.get('pass')
        email = request.GET.get('email')
        pattern = re.compile("[A-Za-z0-9_-]+")
        if not pattern.fullmatch(username):
            return render(request, "utils/dummy.html", {"result": 'Incorrect Characters'})
        else:
            try:
                user = User.objects.filter(username=username)[0]
                return render(request, "utils/dummy.html", {"result": 'Username Taken'})
            except:
                try:
                    user = User.objects.filter(email=email)[0]
                    return render(request, "utils/dummy.html", {"result": 'Email Taken'})
                except:
                    user = User(username=username)
                    user.email = email
                    try:
                        userToken = request.COOKIES['userToken']
                    except:
                        userToken = None
                    if userToken:
                        try:
                            anon_user = User.objects.filter(userToken=userToken, anon=True)[0]
                            anon_user.anon = False
                            anon_user.username = user.username
                            anon_user.email = user.email
                            user = anon_user
                        except:
                            pass
                    user.set_password(password)
                    user.slugger()
                    user.save()
                    user = authenticate(username=username, password=password)
                    login(request, user)
                    if not user.appToken:
                        from uuid import uuid4
                        rand_token = uuid4()
                        # prnt(rand_token)
                        user.appToken = rand_token
                        user.save()
                    return render(request, "utils/dummy.html", {"result": user.appToken})
    except Exception as e:
        prnt(str(e))
        return render(request, "utils/dummy.html", {"result": 'Fail'})

def user_view(request, username):
    prnt('profile')
    username = username.replace('|', '')
    prnt('username',username)
    u = User.objects.get(display_name=username)
    title = 'V/%s' %(str(u.display_name))
    prnt('title',title)
    cards = 'user_view'
    style = request.GET.get('style', 'index')
    # sort = request.GET.get('sort', 'alphabetical')
    page = request.GET.get('page', 1)
    view = request.GET.get('view', 'all')
    topicList = []
    options = {'Votes':'%s?view=Votes'%(u.get_absolute_url()), 'Cheers':'cheer','Statements':'%s?view=Statements'%(u.get_absolute_url()), 'Replies':'%s?view=Replies'%(u.get_absolute_url()),  'Polls':'%s?view=Polls'%(u.get_absolute_url()), 'Petitions':'%s?view=Petitions'%(u.get_absolute_url()), 'Saved': '%s?view=Saved'%(u.get_absolute_url()), 'Following': '%s?view=Following'%(u.get_absolute_url())}
    if style == 'index':
        context = {
            'title': title,
            'cards': cards,
            'view': view,
            'user': u,
            'nav_bar': list(options.items()),
        }
        return render_view(request, context)
    else:
        # roles = Role.objects.filter(position='Member of Parliament', end_date=None).select_related('person').order_by('person')
        if view == 'all':
            posts = Reaction.objects.filter(user=u).filter(Q(isYea=True)|Q(isNay=True)|Q(saved=True)).select_related('post').order_by('-updated')
        elif view == 'Votes':
            posts = Reaction.objects.filter(user=u).filter(Q(isYea=True)|Q(isNay=True)).exclude(isPreviousVote=True).select_related('post').order_by('-updated')
        elif view == 'nays': 
            posts = Reaction.objects.filter(user=u).filter(isNay=True).select_related('post').order_by('-updated')
        elif view == 'Saved':
            posts = Reaction.objects.filter(user=u).filter(saved=True).select_related('post').order_by('-updated')
        elif view == 'Following':
            getList = []
            for p in u.follow_person.all():
                # prnt(p)
                getList.append(p)
            for p in u.follow_bill.all():
                # prnt(p)
                getList.append(p.get_latest_version())
            for p in u.follow_committee.all():
                # prnt(p)
                getList.append(p)
            for p in u.get_follow_topics():
                # prnt(p)
                getList.append(p)
            posts = getList
            # prnt(getList)
            # tmp = Archive.objects.filter(keywords__icontains='Escorted temporary absence')
            # prnt(tmp.count())
            # posts = Post.objects.filter(keywords__overlap=getList).select_related('committeeMeeting', 'committeeItem','bill','hansardItem').order_by('-date_time')
            # prnt(posts.count())
            # posts = Post.objects.filter(Q(committeeMeeting__committee__in=committees)|Q(bill__in=bills)|Q(hansardItem__person__in=people)|Q(committeeItem__person__in=people)|Q(hansardItem__Terms__contains=topicList)|Q(committeeItem__Terms__contains=topicList)).order_by('-date_time')
            # prnt('posts')
        elif view == 'constituency':
            # prnt('con')
            if not u.riding:  
                response = redirect('/user/%s/set-constituency' %(str(u.username)))
                prnt(response)
                return response
        elif view == 'province':
            pass
        elif view == 'municipality':
            pass
        setlist = paginate(posts, page, request)
        # for i in setlist:
        #     prnt(i, i.id, i.postId, i.post)
        context = {
            'title': title,
            'cards': cards,
            'view': view,
            'user': u,
            'nav_bar': list(options.items()),
            'feed_list':setlist,
            'topicList': topicList,
        }
    return render_view(request, context)


def user_settings_view(request):
    # username = username.replace('|', '')
    # u = User.objects.get(display_name=username)
    u = request.user
    title = 'V|%s settings' %(str(u.display_name))
    cards = 'user_settings'
    style = request.GET.get('style', 'index')
    context = {
        'title': title,
        'cards': cards,
    }
    return render_view(request, context)


def user_set_region_view(request):
    prnt('profile')
    # username = username.replace('|', '')
    u = request.user
    
    title = 'My Region'
    cards = 'region_form'
    style = request.GET.get('style', 'index')
    # sort = request.GET.get('sort', 'alphabetical')
    # page = request.GET.get('page', 1)
    view = request.GET.get('view', 'constituency')
    address = request.POST.get('address')
   
    # from django.contrib.gis.utils import GeoIP
    # g = GeoIP()
    # ip = request.META.get('REMOTE_ADDR', None)
    # prnt(ip)
    # if ip:
    #     city = g.city(ip)['city']
    # else:
    #     city = 'Rome'
    # prnt('city: ', city)

    # import pygeoip
    # gi = pygeoip.GeoIP(GEOIP_DATABASE, pygeoip.GEOIP_STANDARD)
    # gi.record_by_addr(ip)

    # https://represent.opennorth.ca/boundaries/?contains=43.349130,-80.317020&format=apibrowser

    prnt(u.postal_code)
    form = RegionForm(initial={'address': u.address})
    if request.method == 'POST':
        # prnt(url)
        
        prnt('GOGO')
        if len(address) <= 7:
            address = address.upper().replace(' ', '')
            u.postal_code = address
            u.address_set_date = datetime.datetime.now()
            u = u.clear_region()
            url = 'https://represent.opennorth.ca/postcodes/%s/' %(address)
            form = u.get_data(url)
        else:
            url = 'http://dev.virtualearth.net/REST/v1/Locations/CA/%s?output=xml&key=AvYxl5kFcs1G1CKjpXM8atABzd_8Wb8shd8OJ2cG3-MtQjOa6Bg7rIOthHLGbDgA' %(address)
            r = requests.get(url)
            soup = BeautifulSoup(r.content, 'lxml')
            latitude = soup.find('latitude').text
            longitude = soup.find('longitude').text
            url = 'https://represent.opennorth.ca/boundaries/?contains=%s,%s' %(latitude, longitude)
            prnt(url)
            u = u.clear_region()
            form = u.get_data(url)
            url = 'https://represent.opennorth.ca/representatives/?point=%s,%s' %(latitude, longitude)
            prnt(url)
            prnt('----------------------------------------------------')
            form = u.get_data(url)
            u.address = address
            u.address_set_date = datetime.datetime.now()
        form = RegionForm(initial={'address': address})
        

        # options = {'All':'%s?view=all'%(u.get_absolute_url()), 'Yeas':'%s?view=yeas'%(u.get_absolute_url()), 'Nays':'%s?view=nays'%(u.get_absolute_url()), 'Comments':'%s?view=comments'%(u.get_absolute_url()), 'Saves': '%s?view=saves'%(u.get_absolute_url()), 'Constituency': '%s?view=constituency'%(u.get_absolute_url()), 'District': '%s?view=district'%(u.get_absolute_url()), 'Municipality': '%s?view=municipality'%(u.get_absolute_url())}
    # prnt(request.user.riding.name)
    # prnt(Person.objects.filter(riding=request.user.riding))
    # try:
    #     MP_role = Role.objects.filter(position='Member of Parliament', riding=request.user.riding, current=True)[0]
    # except:
    #     MP_role = 'Seat is vacant'
    # try:
    #     MPP_role = Role.objects.filter(position='MPP', district=request.user.district, current=True)[0]
    # except:
    #     MPP_role = None
    # try:
    #     Mayor_role = Role.objects.filter(position='Mayor', municipality=request.user.municipality, current=True)[0]
    # except:
    #     Mayor_role = None
    # try:
    #     Councillor_role =  Role.objects.filter(position='Councillor', ward=request.user.ward, current=True)[0]
    # except:
    #     Councillor_role = None
    reps = get_reps(request.user)
    # prnt(reps)
    context = {
        'u': u,
        'title': title,
        'cards': cards,
        'view': view,
        # 'nav_bar': list(options.items()),
        # 'feed_list':setlist,
        'form': form,
        # 'MP_role': MP_role,
        # 'MPP_role': MPP_role,
        # 'Mayor_role': Mayor_role,
        # 'Councillor_role': Councillor_role,
    }
    context = {**reps, **context}
    return render_view(request, context)


@csrf_exempt
def receive_interaction_data_view(request):
    prnt('receive_interaction_data_view')
    if request.method == 'POST':
        # prnt(request.body)
        # postData = json.loads(request.body)
        data = json.loads(request.POST.get('objData'))
        # prnt(data)
        # data = postData['objData']
        # prnt(received_json)
        # newPrivateKey = request.POST.get('new_private_key')
        # newPublicKey = request.POST.get('new_public_key')
        publicKey = data['publicKey']
        # transaction_data = request.POST.get('transactionData')
        signature = data['signature']
        # transaction_data = "Your transaction data here"
        # prnt('privateKey', newPrivateKey)
        # prnt()
        # prnt('pubkey', newPublicKey)
        prnt()
        prnt('publicKey', publicKey)
        # prnt()
        prnt('sig', signature)
        try:
            user = request.user
            prnt('user found', user)
            # if user.must_rename:
            #     if User.objects.filter(display_name=userData['display_name']).exclude(id=userData['id']).count() > 0:
            #         return JsonResponse({'message' : 'Username taken'})
            #     else:
            x = get_signing_data(data)
            # else:
            #     x = get_signing_data(user)
            # prnt(x)
            # user.delete()
            # for i in UserPubKey.objects.all():
            #     prnt(i.publicKey)
            #     prnt(i.User_obj.display_name)
            # prnt('--')
            
            try:
                upk = UserPubKey.objects.filter(User_obj=user, publicKey=publicKey)[0]
                prnt(upk)
                # prnt(signature)
                # prnt(x)
                is_valid = upk.verify(x, signature)
                prnt('is_valid',is_valid)
                if is_valid:
                    # json_data = json.loads(data)

                    xModel = get_or_create_model(data['object_type'], id=data['id'])
                    # prnt('xModel',xModel)
                    # xModel.User_obj = user
                    xModel, good = sync_and_share_object(xModel, data)
                    prnt('good',good)
                    if good:
                        response = JsonResponse({'message' : 'Success'})
                        # response.set_cookie(key='userData', value=json.dumps(x), expires=datetime.datetime.today()+datetime.timedelta(days=3650))
                        return response
                    else:
                        return JsonResponse({'message' : 'Sync failed'})
                else:
                    return JsonResponse({'message' : 'Verification failed'})
            except Exception as e:
                prnt(str(e))
                return JsonResponse({'message' : 'Invalid publicKey'})
        except Exception as e:
            return JsonResponse({'message' : f'Error {str(e)}'})

@csrf_exempt
def reaction_view(request, iden, item):
    prnt('reaction', iden, item)
    # add reaction to dataToShare


    userToken = None
    if not request.user.is_authenticated:
        # post = Post.objects.filter(id=iden)[0]
        # if item == 'None' or item == 'yea' or item == 'nay':
        #     try:
        #         userToken = request.COOKIES['userToken']
        #         if userToken:
        #             user = User.objects.filter(userToken=userToken)[0]
        #     except:
        #         userToken = uuid4()
        #         from random_username.generate import generate_username
        #         rand_username = generate_username(1)[0]
        #         user = User(username=rand_username, userToken=userToken, anon=True)
        #         user.slugger()
        #         user.save()
        # else:
        return render(request, "utils/dummy.html", {'result':'Login'})
        # user = User.objects.filter(username='Anon')[0]
    else:
        user = request.user
        # userOptions = UserOptions.objects.filter(pointerId=user.id)[0]
    if not 'person' in item:
        post = Post.objects.filter(id=iden).first()
        if not post:
            post = Archive.objects.filter(id=iden).first()
        # try:
            # if previous interaction has yet to be shared in dataPacket, reuse, otherwise create new
            # vote = 
            
            
            
        #     interaction = Interaction.objects.filter(User_obj=user, pointerId=post.pointerId).order_by('-created')[0]
        #     # dataPacket = get_latest_dataPacket()
        #     # packet_data = json.loads(dataPacket.data)
        #     # if interaction.id not in packet_data:
        #     #     fail
        #     # prnt(r.count())
        #     # post = r[0].post
        #     # try:
        #     #     r[1].delete()
        #     #     prnt('r[1].deleted')
        #     # except Exception as e:
        #     #     prnt(str(e))
        #     # interaction = r[0]
        # except Exception as e:
        #     prnt('create r', str(e))
        #     # post_pointer = post.pointer()
        #     interaction_id = hashlib.md5(str(user.id + post.id).encode('utf-8')).hexdigest()
        #     interaction = Interaction(id=interaction_id, created=now_utc(), User_obj=user, pointerId=post.pointerId, pointerType=post.pointerType, Region_obj=post.Region_obj)
        #     if post.object_type == 'Post':
        #         interaction.Post_obj=post
        #     elif post.object_type == 'Archive':
        #         interaction.Archive_obj=post
        #     interaction.save()
            
    # prnt(item)
    if item == 'None' or item == 'yea' or item == 'nay':
        # prnt('is vote')
        # interaction.isYea = False
        # interaction.isNay = False
        reuse = False
        vote = UserVote.objects.filter(User_obj=user, postId=post.id).first()
        if vote:
            reuse = check_dataPacket(vote)
        if not reuse:
            # prnt(str(e))
            vote = UserVote(User_obj=user, postId=post.id, pointerId=post.pointerId, id=hash_obj_id('UserVote'), created=now_utc())
            from blockchain.models import Blockchain
            blockchain = Blockchain.objects.filter(genesisId=post.Region_obj.id).first()
            vote.blockchainId = blockchain.id
        # prnt(vote)
        # prnt('return')
        return JsonResponse({'message' : 'Please fill, sign and return', 'data' : get_signing_data(vote)})

    #     vote.vote = item
        

    #     if interaction.isYea == True:
    #         interaction.calculate_vote('yea', False)
    #     elif interaction.isNay == True:
    #         interaction.calculate_vote('nay', False)
    # elif item == 'yea':

    #     vote = interaction.get_or_create_object('Vote_obj', id=uuid.uuid4().hex, created=now_utc(), pointerId=post.id, Region_obj=post.Region_obj)
    #     vote.vote = 'yea'
    #     # vote = interaction.UserVote_obj
    #     # reuse = check_dataPacket(vote)
    #     # if reuse:
    #     #     vote.vote = 'yea'
    #     # else:
    #     #     vote = UserVote(id=uuid.uuid4().hex, created=now_utc(), pointerId=post.id, Region_obj=post.Region_obj)

    #     # interaction.isYea = True
    #     # interaction.isNay = False
    #     # r.viewed = True
    #     interaction.calculate_vote('yea', False)
    #     # if r.isYea:
    #     #     # prnt('1')
    #     #     r.isYea = False
    #     # else:
    #     #     prnt('2')
    #     #     r.isYea = True
    #     #     r.isNay = False
    # elif item == 'nay':

    #     vote = interaction.get_or_create_object('Vote_obj', id=uuid.uuid4().hex, created=now_utc(), pointerId=post.id, Region_obj=post.Region_obj)
    #     vote.vote = 'nay'

    #     interaction.isYea = False
    #     interaction.isNay = True
    #     # r.viewed = True
    #     interaction.calculate_vote('nay', False)
    #     # if r.isNay:
    #     #     r.isNay = False
    #     # else:
    #     #     r.isNay = True
    #     #     r.isYea = False
    elif item == 'saveButton':
        # if interaction.saved == True:
        #     interaction.saved = False
        # else:
        #     interaction.saved = True
        #     interaction.saved_time = now_utc()
        reuse = False
        save = SavePost.objects.filter(User_obj=user, postId=post.id).first()
        if save:
            reuse = check_dataPacket(save)
            # prnt('reuse', reuse)
        if not reuse:
            # prnt(str(e))
            save = SavePost(User_obj=user, postId=post.id, pointerId=post.pointerId, id=hash_obj_id('SavePost'), created=now_utc())
            
        return JsonResponse({'message' : 'Please fill, sign and return', 'data' : get_signing_data(save)})

    elif item == 'follow' or item == 'unfollow':
        prnt('follow')
        # r.viewed = True
        if not post:
            post = Post.objects.filter(id=iden).first()
            if not post:
                post = Archive.objects.filter(id=iden).first()

        # user.follow_Bill_objs.add(post.Bill_obj)
        # f = user.follow_Bill_obj_id_array.append(post.Bill_obj.id)
        # prnt(f)
        # user.save()
        # prnt(get_signing_data(user))
        return JsonResponse({'message' : 'Please fill, sign and return', 'data' : get_signing_data(user)})
        # prnt(post)
        # prnt(r.follow)
        # if r.follow == True:
        #     r.follow = False
        #     if post.bill:
        #         # prnt('bv')
        #         userOptions.follow_bill.remove(post.bill)
        #         text = 'Unfollow Bill %s' %(post.bill.NumberCode)
        #     elif post.committeeMeeting:
        #         # prnt(post.committeeMeeting.committee)
        #         userOptions.follow_committee.remove(post.committeeMeeting.committee)
        #         text = 'Unfollow Committee %s' %(post.committeeMeeting.committee.Title)
        #     elif post.committeeItem:
        #         userOptions.follow_person.remove(post.committeeItem.person)
        #         text = 'Unfollow %s' %(post.committeeItem.person.full_name)
        #     elif post.hansardItem:
        #         userOptions.follow_person.remove(post.hansardItem.person)
        #         text = 'Unfollow %s' %(post.hansardItem.person.full_name)
        # else:
        #     r.follow = True
        #     if post.bill:
        #         userOptions.follow_bill.add(post.bill)
        #         text = 'Following Bill %s' %(post.bill.NumberCode)
        #     elif post.committeeMeeting:
        #         userOptions.follow_committee.add(post.committeeMeeting.committee)
        #         text = 'Following Committee %s' %(post.committeeMeeting.committee.Title)
        #     elif post.committeeItem:
        #         userOptions.follow_person.add(post.committeeItem.person)
        #         text = 'Following %s' %(post.committeeItem.person.full_name)
        #     elif post.hansardItem:
        #         userOptions.follow_person.add(post.hansardItem.person)
        #         text = 'Following %s' %(post.hansardItem.person.full_name)
        # userOptions.save()
        # r.save()
        # text = 'n'
        # return render(request, "utils/dummy.html", {'result':text})
    elif item == 'follow-person':
        # prnt('follow person')
        # r.viewed = True
        person = Person.objects.filter(id=iden).first()
        if person in userOptions.follow_person.all():
            userOptions.follow_person.remove(person)
        else:
            userOptions.follow_person.add(person)
        userOptions.save()
        # prnt(user.follow_person.all())
        return render(request, "utils/dummy.html", {'result':item})
    # r.save()
    # prnt(r)
    # context = {'result':item}
    # response =  render(request, "utils/dummy.html", context)
    # if userToken:
    #     response.set_cookie(key='userToken', value=userToken, expires=datetime.datetime.today()+datetime.timedelta(days=3650))
    # return response
    return JsonResponse({'message' : 'Please sign and return', 'userData' : get_signing_data(user)})
        
@csrf_exempt
def receive_test_data_view(request):
    prnt('recieive test')
    # prnt(request.body)
    # prnt()
    localData = json.loads(request.POST.get('localData'))
    prnt(localData)
    prnt()
    serverData = json.loads(request.POST.get('serverData'))
    prnt(serverData)
    # del serverData['signature']
    # del serverData['publicKey']
    prnt()
    # siglessData = json.loads(request.POST.get('siglessData'))
    # prnt(siglessData)

    prnt()
    if serverData == localData:
        prnt('its the same')
    else:
        prnt('no they are different')

    prnt()


    # publicKey = serverData['publicKey']
    # signature = serverData['signature']
    # # try:
    # user = request.user
    # # prnt('user found', user)
    # x = get_signing_data(serverData)
    #     # try:
    # upk = UserPubKey.objects.filter(User_obj=user, publicKey=publicKey)[0]
    
    # is_valid = upk.verify(x, signature)
    # prnt('serverData is_valid',is_valid)
    # prnt()

    publicKey = localData['publicKey']
    signature = localData['signature']
    # try:
    user = request.user
    # prnt('user found', user)
    x = get_signing_data(localData)
        # try:
    upk = UserPubKey.objects.filter(User_obj=user, publicKey=publicKey).first()
    
    is_valid = upk.verify(x, signature)
    prnt('localData is_valid',is_valid)
    prnt()

    xModel, good = sync_and_share_object(user, localData)
    prnt('good',good)
    prnt()

@csrf_exempt
def set_sonet_view(request):
    prnt('---set_sonet_view')
    try:
        err = 1
        if request.method == 'POST':
            existing_net = Sonet.objects.first()
            if existing_net:
                sonet_exists = True
            else:
                sonet_exists = False

            raw_data = request.body.decode('utf-8')
            received_data = json.loads(raw_data)

            # userData = json.loads(received_data.get('userData'))
                
            # sonetData = request.POST.get('sonetData')
            sonetData_json = json.loads(received_data.get('sonetData'))
            prnt('sonetData_json',sonetData_json)
            err = 2
            sonet = get_or_create_model('Sonet', id=sonetData_json['id'])
            prnt('sonet obj',sonet)
            err = 3
            sonet, valid_obj, updatedDB = sync_model(sonet, sonetData_json)
            prnt('sonet-good',valid_obj)
            err = 4
            if not valid_obj:
                return JsonResponse({'message' : 'A problem occured - obj not valid'})
            elif updatedDB:
                if not sonet_exists:
                    err = 5
                    from blockchain.models import Node, Plugin
                    node = Node()
                    node.id = hash_obj_id(node)
                    err = 6
                    earth = Region(created=now_utc(), func='super', nameType='Planet', Name='Earth', modelType='planet', LogoLinks={"flag":"img/earth_pic.jpg"})
                    earth.id = hash_obj_id(earth, len=0)
                    err = 7

                    accounts = Plugin(app_name='accounts', Title='Accounts', app_dir='../accounts')
                    accounts.initialize()
                    err = 8
                    blockchain = Plugin(app_name='blockchain', Title='Blockchain', app_dir='../blockchain')
                    blockchain.initialize()
                    err = 9
                    posts = Plugin(app_name='posts', Title='Posts', app_dir='../posts')
                    posts.initialize()
                    err = 10
                    transactions = Plugin(app_name='transactions', Title='Transactions', app_dir='../transactions')
                    transactions.initialize()
                    legis = Plugin(app_name='legis', Title='SoVote', app_dir='../legis')
                    legis.initialize()
                    err = 11
                    return JsonResponse({'message' : 'Success', 'sonet' : get_signing_data(sonet), 'earth' : get_signing_data(earth), 'node' : get_signing_data(node), 'accounts':get_signing_data(accounts),'blockchain':get_signing_data(blockchain),'posts':get_signing_data(posts),'transactions':get_signing_data(transactions),'legis':get_signing_data(legis)})
                else:
                    err = 8
                    return JsonResponse({'message' : 'Success', 'sonet' : get_signing_data(sonet)})
            else:
                return JsonResponse({'message' : 'Not Saved'})
    except Exception as e:
        return JsonResponse({'message' : f'A problem occured, {str(e)} -- err:{err}'})
        
@csrf_exempt
def verify_superuser_view(request):
    prnt('---verify_superuser_view')
    try:
        if request.method == 'POST':
            user_id = request.POST.get('user_id')
            signed_obj = json.loads(request.POST.get('signed_obj'))
            publicKey = request.POST.get('publicKey')
            signature = request.POST.get('signature')
            # from blockchain.models import round_time
            x = dt_to_string(round_time(dt=now_utc(), dir='down', amount='evenhour'))
            proceed = True
            is_super = False
            if proceed and signed_obj['dt'] != x:
                proceed = False
            if proceed:
                user = User.objects.filter(id=user_id).first()
                if not user:
                    proceed = False
                else:
                    if user.assess_super_status():
                        is_super = user.verify_sig(signed_obj, signature)
            return JsonResponse({'message' : 'success', 'is_super':is_super})


    except Exception as e:
        return JsonResponse({'message' : f'A problem occured, {str(e)}'})
        

