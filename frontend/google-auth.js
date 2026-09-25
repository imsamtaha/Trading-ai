import {createClient} from '@supabase/supabase-js';
import {AUTH_ORIGIN, PUBLIC_KEY, AUTH_OPTIONS, startGoogleSignIn, finishGoogleSignIn, googleProviderReady} from './google-auth-core.mjs';

const messages = {
  en: {
    button:'Continue with Google', out:'Sign out', busy:'Please wait…',
    ready:'Create an account or sign in with your Google account.',
    setup:'Google sign-up is not available yet. Please try again after setup is complete.',
    unavailable:'Sign-in is temporarily unavailable. Please try again.',
    callback:'Sign-in was cancelled or could not be completed. Please try again.',
    session:'Your session could not be verified. Please try signing in again.',
    signed:'Signed in as ', signedOut:'You are signed out.', outError:'Could not sign out. Please try again.',
    storage:'Allow browser storage to use Google sign-in.',
  },
  ar: {
    button:'المتابعة باستخدام Google', out:'تسجيل الخروج', busy:'يرجى الانتظار…',
    ready:'أنشئ حسابًا أو سجّل الدخول باستخدام حسابك على Google.',
    setup:'التسجيل باستخدام Google غير متاح بعد. يرجى المحاولة بعد اكتمال الإعداد.',
    unavailable:'تسجيل الدخول غير متاح مؤقتًا. يرجى المحاولة مجددًا.',
    callback:'تم إلغاء تسجيل الدخول أو تعذّر إكماله. يرجى المحاولة مجددًا.',
    session:'تعذّر التحقق من جلستك. يرجى تسجيل الدخول مجددًا.',
    signed:'تم تسجيل الدخول باسم ', signedOut:'تم تسجيل خروجك.', outError:'تعذّر تسجيل الخروج. يرجى المحاولة مجددًا.',
    storage:'اسمح بالتخزين في المتصفح لاستخدام تسجيل الدخول عبر Google.',
  },
};
const button=document.getElementById('google-sign-in');
const logout=document.getElementById('google-sign-out');
const status=document.getElementById('account-status');
let user=null, busy=true, message='ready', verification=0;
const text=()=>messages[document.documentElement.lang==='ar'?'ar':'en'];
function render() {
  button.hidden=!!user;
  logout.hidden=!user;
  button.disabled=logout.disabled=busy || !client;
  button.textContent=busy?text().busy:text().button;
  logout.textContent=text().out;
  status.textContent=message==='outError'?text().outError:(user?text().signed+(user.email || user.id):text()[message]);
  status.dir='auto';
}
let client;
try {
  localStorage.setItem('atlas-storage-check','1');
  localStorage.removeItem('atlas-storage-check');
  client=createClient(AUTH_ORIGIN,PUBLIC_KEY,{auth:AUTH_OPTIONS});
} catch {message='storage';busy=false;}
window.atlasAuth={getSession:async()=>{if(!client)return null;const {data,error}=await client.auth.getSession();if(error)return null;return data.session||null;},getUser:()=>user};
function emitAuthChange(){window.dispatchEvent(new CustomEvent('atlas-auth-change'));}

async function verify(href=location.origin + '/') {
  const request=++verification;
  try {
    const current=await finishGoogleSignIn({auth:client.auth,href,replaceUrl:path=>history.replaceState(null,'',path)});
    if(request!==verification)return;
    user=current; message='ready';
    if(!current) {
      const ready=await googleProviderReady(fetch);
      if(request!==verification)return;
      message=ready?'ready':'setup';
    }
  } catch(error) {
    if(request!==verification)return;
    user=null;message=error.message in text()?error.message:'unavailable';
  } finally {if(request===verification){busy=false;render();emitAuthChange();}}
}
button.addEventListener('click',async()=>{
  if(!client)return;
  busy=true;message='ready';render();
  try {
    const url=await startGoogleSignIn({auth:client.auth,fetcher:fetch,origin:location.origin,language:document.documentElement.lang});
    location.assign(url);
  } catch(error){message=error.message==='setup'?'setup':'unavailable';busy=false;render();}
});
logout.addEventListener('click',async()=>{
  busy=true;render();++verification;
  try {
    const {error}=await client.auth.signOut({scope:'local'});
    if(error)throw error;
    user=null;message='signedOut';
  } catch {message='outError';}
  finally {busy=false;render();emitAuthChange();}
});
document.addEventListener('atlas-language-change',render);
window.addEventListener('atlas-language-change',render);
if(client) {
  client.auth.onAuthStateChange(event=>{
    if(event==='SIGNED_OUT'){++verification;user=null;busy=false;message='signedOut';render();emitAuthChange();}
    if(event==='TOKEN_REFRESHED' || event==='SIGNED_IN') queueMicrotask(()=>verify());
  });
  verify(location.href);
}
render();
