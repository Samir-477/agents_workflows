"use client";

import { useEffect, useState } from "react";

import {
  deleteProviderKey,
  getProviderSettings,
  saveProviderKey,
  saveModelSelection,
  type ProviderKeyStatus,
  type ProviderName,
  type ProviderSettingsResponse,
} from "@/lib/settings-api";

function sourceLabel(item: ProviderKeyStatus): string {
  if (item.source === "database") return "Supabase Vault";
  if (item.source === "environment") return "Deployment environment";
  return "Not configured";
}

export function SettingsPage() {
  const [settings, setSettings] = useState<ProviderSettingsResponse | null>(null);
  const [values, setValues] = useState<Record<ProviderName, string>>({ groq: "" });
  const [selectedModel, setSelectedModel] = useState("");
  const [busy, setBusy] = useState<ProviderName | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    getProviderSettings()
      .then((response) => {
        setSettings(response);
        setSelectedModel(response.active_model ?? response.model_options[0]?.id ?? "");
      })
      .catch((caught) => setError(caught instanceof Error ? caught.message : "Unable to load settings."));
  }, []);

  async function save(provider: ProviderName) {
    const key = values[provider].trim();
    if (!key) return;
    setBusy(provider);
    setError("");
    setNotice("");
    try {
      setSettings(await saveProviderKey(provider, key));
      setValues((current) => ({ ...current, [provider]: "" }));
      setNotice("Groq key updated. New runs will use it immediately.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The key could not be saved.");
    } finally {
      setBusy(null);
    }
  }

  async function saveModel() {
    if (!selectedModel) return;
    setBusy("groq");
    setError("");
    setNotice("");
    try {
      const response = await saveModelSelection(selectedModel);
      setSettings(response);
      setSelectedModel(response.active_model ?? selectedModel);
      setNotice("Active model updated. New runs will use it immediately.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The model could not be saved.");
    } finally {
      setBusy(null);
    }
  }

  async function remove(provider: ProviderName) {
    if (!window.confirm("Remove this saved override? The environment key will be used if one exists.")) return;
    setBusy(provider);
    setError("");
    setNotice("");
    try {
      setSettings(await deleteProviderKey(provider));
      setNotice("Saved override removed.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The saved key could not be removed.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="mx-auto max-w-[1040px] px-5 py-12 sm:px-8 sm:py-16">
      <div className="max-w-3xl">
        <p className="font-mono text-xs font-semibold uppercase tracking-[0.2em] text-[#5549dd]">Workspace controls</p>
        <h1 className="mt-2 text-4xl font-semibold tracking-[-0.045em] text-[#171820] sm:text-5xl">Settings</h1>
        <p className="mt-4 text-base leading-7 text-[#676770]">Manage the Groq credential and language model used by your agents. Saved changes affect new runs immediately.</p>
      </div>

      <section className="mt-10 overflow-hidden rounded-[24px] border border-[#dfdedb] bg-white shadow-[0_18px_60px_rgba(35,31,27,0.05)]">
        <div className="border-b border-[#eceae6] px-6 py-6 sm:px-8">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.18em] text-[#ff5738]">API keys</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-[-0.025em]">Groq model settings</h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-[#6d6c74]">Keys saved here are encrypted by Supabase Vault. The browser receives only a masked suffix and can never retrieve the full value.</p>
            </div>
            {settings ? (
              <div className="rounded-xl border border-[#dedafc] bg-[#f6f4ff] px-4 py-3 text-right text-xs text-[#5b50bd]">
                <p className="font-semibold">Active: {settings.active_provider ?? "Not set"}</p>
                <p className="mt-1 max-w-[260px] truncate font-mono">{settings.active_model ?? "No model configured"}</p>
              </div>
            ) : null}
          </div>
        </div>

        {error ? <p className="border-b border-red-100 bg-red-50 px-6 py-3 text-sm text-red-700 sm:px-8">{error}</p> : null}
        {notice ? <p className="border-b border-emerald-100 bg-emerald-50 px-6 py-3 text-sm text-emerald-800 sm:px-8">{notice}</p> : null}

        <div className="grid gap-5 p-5 sm:p-8 md:grid-cols-2">
          {settings ? settings.providers.map((item) => (
            <article key={item.provider} className="rounded-[20px] border border-[#e4e2de] bg-[#fcfbf9] p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-lg font-semibold text-[#202129]">{item.label}</h3>
                  <p className="mt-1 text-xs text-[#85838b]">{sourceLabel(item)}</p>
                </div>
                <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${item.configured ? "bg-[#eaf7ef] text-[#24724f]" : "bg-[#f0efed] text-[#77757a]"}`}>
                  {item.configured ? "Configured" : "Missing"}
                </span>
              </div>

              <div className="mt-5 rounded-xl border border-[#e0ded9] bg-white px-4 py-3 font-mono text-sm text-[#56545c]">
                {item.masked_key ?? "No API key saved"}
              </div>

              <label htmlFor={`${item.provider}-key`} className="mt-5 block text-xs font-semibold text-[#45454d]">Replace API key</label>
              <input
                id={`${item.provider}-key`}
                type="password"
                autoComplete="new-password"
                value={values[item.provider]}
                onChange={(event) => setValues((current) => ({ ...current, [item.provider]: event.target.value }))}
                placeholder="gsk_..."
                className="mt-2 h-11 w-full rounded-xl border border-[#dcdad6] bg-white px-4 text-sm outline-none placeholder:text-[#aaa8ad] focus:border-[#5a4df4] focus:ring-4 focus:ring-[#5a4df4]/10"
              />
              <div className="mt-4 flex flex-wrap gap-2">
                <button type="button" onClick={() => save(item.provider)} disabled={!values[item.provider].trim() || busy !== null} className="rounded-xl bg-[#ff5738] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#e9482b] disabled:cursor-not-allowed disabled:opacity-45">
                  {busy === item.provider ? "Saving…" : "Save key"}
                </button>
                {item.source === "database" ? (
                  <button type="button" onClick={() => remove(item.provider)} disabled={busy !== null} className="rounded-xl border border-[#dedbd6] bg-white px-4 py-2.5 text-sm font-semibold text-[#55545c] transition hover:bg-[#f5f3ef] disabled:opacity-45">Remove override</button>
                ) : null}
              </div>
              {item.updated_at ? <p className="mt-4 text-[11px] text-[#949299]">Updated {new Date(item.updated_at).toLocaleString()}</p> : null}
            </article>
          )) : <p className="text-sm text-[#777680]">Loading provider settings…</p>}

          {settings ? (
            <article className="rounded-[20px] border border-[#e4e2de] bg-[#fcfbf9] p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-lg font-semibold text-[#202129]">LLM model</h3>
                  <p className="mt-1 text-xs text-[#85838b]">Saved in Supabase · {settings.model_source} selection</p>
                </div>
                <span className="rounded-full bg-[#f2f0ff] px-2.5 py-1 text-[11px] font-semibold text-[#4b3fca]">Groq hosted</span>
              </div>

              <label htmlFor="groq-model" className="mt-5 block text-xs font-semibold text-[#45454d]">Model used for new runs</label>
              <select
                id="groq-model"
                value={selectedModel}
                onChange={(event) => setSelectedModel(event.target.value)}
                className="mt-2 h-11 w-full rounded-xl border border-[#dcdad6] bg-white px-4 text-sm font-medium text-[#34343d] outline-none focus:border-[#5a4df4] focus:ring-4 focus:ring-[#5a4df4]/10"
              >
                {settings.model_options.map((model) => (
                  <option key={model.id} value={model.id}>{model.label} — {model.release_tier}</option>
                ))}
              </select>

              <div className="mt-4 rounded-xl border border-[#e0ded9] bg-white px-4 py-3">
                <p className="font-mono text-xs text-[#585660]">{selectedModel}</p>
                <p className="mt-2 text-xs leading-5 text-[#85838b]">Production models are the safer default. Preview models can change or be retired by Groq.</p>
              </div>

              <button type="button" onClick={saveModel} disabled={!selectedModel || selectedModel === settings.active_model || busy !== null} className="mt-4 rounded-xl bg-[#5a4df4] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#493dcf] disabled:cursor-not-allowed disabled:opacity-45">
                {busy === "groq" ? "Saving…" : "Use this model"}
              </button>
            </article>
          ) : null}
        </div>
      </section>

      <div className="mt-6 rounded-[18px] border border-[#ddd8ff] bg-[#f5f3ff] px-5 py-4 text-sm leading-6 text-[#574f9d]">
        Environment variables remain the fallback. Removing the Vault key override does not delete a Groq key configured in Vercel or your local environment.
      </div>
    </main>
  );
}
