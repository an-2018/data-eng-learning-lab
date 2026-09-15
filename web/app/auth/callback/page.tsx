'use client';
import {useEffect,useState} from 'react';
import {auth} from '@/lib/api';
export default function Callback(){const [error,setError]=useState('');useEffect(()=>{auth().signinRedirectCallback().then(()=>window.location.replace('/')).catch(()=>setError('Sign-in failed. Return to the home page and try again.'));},[]);return <main className="login"><h1>{error||'Completing sign-in…'}</h1><a href="/">Return home</a></main>}
