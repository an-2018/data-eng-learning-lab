import { UserManager, WebStorageStateStore } from 'oidc-client-ts';
export const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const dev = process.env.NEXT_PUBLIC_DEV_AUTH === 'true';
let manager: UserManager | undefined;
export function auth() {
  if (!manager) manager = new UserManager({authority:process.env.NEXT_PUBLIC_OIDC_AUTHORITY || '',client_id:process.env.NEXT_PUBLIC_OIDC_CLIENT_ID || '',redirect_uri:window.location.origin+'/auth/callback',response_type:'code',scope:'openid profile email',userStore:new WebStorageStateStore({store:window.sessionStorage})});
  return manager;
}
export async function token() {if (dev) return 'local-development'; return (await auth().getUser())?.id_token;}
export async function login() {await auth().signinRedirect();}
export async function api<T=any>(path:string, options:RequestInit={}) : Promise<T> {
  const access = await token();
  const response = await fetch(API+path,{...options,headers:{'Content-Type':'application/json',...(access?{Authorization:`Bearer ${access}`} : {}),...options.headers}});
  if (!response.ok) {const data=await response.json().catch(()=>({})); throw new Error(typeof data.detail==='string'?data.detail:`Request failed (${response.status})`);}
  return response.json();
}
export const post=(path:string,body?:unknown)=>api(path,{method:'POST',body:body===undefined?undefined:JSON.stringify(body)});
