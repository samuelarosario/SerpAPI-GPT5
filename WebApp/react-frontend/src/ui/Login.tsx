import React, { useState } from 'react';

type Props = { onLogin: (accessToken: string, refreshToken?: string) => void };

export default function Login({ onLogin }: Props) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null); setBusy(true);
    try {
      const r = await fetch('/auth/login', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      if(!r.ok){
        const txt = await r.text().catch(()=> '');
        setError(`Login failed (${r.status}). ${txt || ''}`); setBusy(false); return;
      }
      const j = await r.json();
      if(!j?.access_token){ setError('No token returned'); setBusy(false); return; }
      localStorage.setItem('access_token', j.access_token);
      if(j.refresh_token) localStorage.setItem('refresh_token', j.refresh_token);
      onLogin(j.access_token, j.refresh_token);
    } catch (e: any) {
      setError(String(e?.message||e));
    } finally {
      setBusy(false);
    }
  }

  function useDemo(){ setEmail('user@local'); setPassword('user'); }

  return (
    <div style={{maxWidth:360, margin:'80px auto', fontFamily:'Inter, system-ui, sans-serif'}}>
      <h2 style={{marginBottom:8}}>Sign in</h2>
      <div style={{color:'#5f6368', marginBottom:16}}>Use your WebApp credentials. For local dev, try the demo user.</div>
      <form onSubmit={submit} style={{display:'flex', flexDirection:'column', gap:10}}>
  <input placeholder="Email" type="text" value={email} onChange={(e)=>setEmail(e.target.value)} required autoComplete="username" />
        <input placeholder="Password" type="password" value={password} onChange={(e)=>setPassword(e.target.value)} required />
        {error && <div style={{color:'#b91c1c'}}>{error}</div>}
        <div style={{display:'flex', gap:8, alignItems:'center'}}>
          <button type="submit" disabled={busy}>{busy? 'Signing in…':'Sign in'}</button>
          <button type="button" onClick={useDemo} disabled={busy}>Use demo</button>
        </div>
      </form>
    </div>
  );
}
