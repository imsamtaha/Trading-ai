import test from 'node:test';
import assert from 'node:assert/strict';
import {AUTH_ORIGIN,AUTH_OPTIONS,callbackUrl,cleanCallbackUrl,startGoogleSignIn,finishGoogleSignIn} from '../frontend/google-auth-core.mjs';

test('OAuth uses PKCE and a same-origin callback with a constrained language',()=>{
  assert.equal(AUTH_OPTIONS.flowType,'pkce');
  assert.equal(AUTH_OPTIONS.detectSessionInUrl,false);
  assert.equal(callbackUrl('https://atlas.example','ar'),'https://atlas.example/?auth=callback&lang=ar');
  assert.equal(callbackUrl('https://atlas.example','evil'),'https://atlas.example/?auth=callback&lang=en');
});
test('disabled Google provider blocks navigation before requesting OAuth',async()=>{
  let called=false;
  await assert.rejects(startGoogleSignIn({
    auth:{signInWithOAuth:async()=>{called=true;}},
    fetcher:async()=>({ok:true,json:async()=>({external:{google:false}})}),
    origin:'https://atlas.example',language:'ar',
  }),/setup/);
  assert.equal(called,false);
});
test('Google sign-in requests only identity scopes and a verified provider URL',async()=>{
  let options;
  const url=await startGoogleSignIn({
    auth:{signInWithOAuth:async args=>{options=args;return {data:{url:AUTH_ORIGIN+'/auth/v1/authorize?provider=google'}};}},
    fetcher:async()=>({ok:true,json:async()=>({external:{google:true}})}),
    origin:'https://atlas.example',language:'ar',
  });
  assert.equal(options.provider,'google');
  assert.equal(options.options.scopes,'openid email profile');
  assert.equal(options.options.redirectTo,'https://atlas.example/?auth=callback&lang=ar');
  assert.equal(new URL(url).origin,AUTH_ORIGIN);
});
test('untrusted OAuth navigation URLs are rejected',async()=>{
  await assert.rejects(startGoogleSignIn({
    auth:{signInWithOAuth:async()=>({data:{url:'https://evil.example/'}})},
    fetcher:async()=>({ok:true,json:async()=>({external:{google:true}})}),
    origin:'https://atlas.example',language:'en',
  }),/unavailable/);
});
test('callback scrubs sensitive parameters before exchanging code and verifies the user',async()=>{
  const calls=[];
  const user=await finishGoogleSignIn({
    href:'https://atlas.example/?auth=callback&lang=ar&code=one-use&state=test',
    replaceUrl:path=>calls.push(['clean',path]),
    auth:{
      exchangeCodeForSession:async code=>{calls.push(['exchange',code]);return {error:null};},
      getUser:async()=>{calls.push(['verify']);return {data:{user:{id:'verified-user'}}};},
    },
  });
  assert.deepEqual(calls,[['clean','/?lang=ar#account'],['exchange','one-use'],['verify']]);
  assert.equal(user.id,'verified-user');
});
test('cancelled or failed callbacks cannot create a signed-in display',async()=>{
  let called=false,cleaned=false;
  await assert.rejects(finishGoogleSignIn({
    href:'https://atlas.example/?auth=callback&error=access_denied&error_description=private',
    replaceUrl:()=>{cleaned=true;},
    auth:{getUser:async()=>{called=true;}},
  }),/callback/);
  assert(cleaned);
  assert.equal(called,false);
  assert.equal(cleanCallbackUrl('https://atlas.example/#access_token=secret&refresh_token=secret'),'/#account');
});
test('missing sessions stay signed out and invalid sessions are not trusted',async()=>{
  assert.equal(await finishGoogleSignIn({
    href:'https://atlas.example/',replaceUrl:()=>{},
    auth:{getUser:async()=>({error:{name:'AuthSessionMissingError'}})},
  }),null);
  await assert.rejects(finishGoogleSignIn({
    href:'https://atlas.example/',replaceUrl:()=>{},
    auth:{getUser:async()=>({error:{name:'AuthApiError'},data:{user:{id:'untrusted'}}})},
  }),/session/);
});
