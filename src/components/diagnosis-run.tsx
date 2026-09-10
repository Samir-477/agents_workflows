"use client";
/* eslint-disable @next/next/no-img-element -- audited external images load only after an explicit user action */
import Link from "next/link";
import { useEffect, useState } from "react";
import { diagnosisAgentRunHref, diagnosisBase, diagnosisLabels, diagnosisRequest, type Case, type Diagnosis, type Evidence, type EvidenceExplanation, type Finding, type ManagementReport } from "@/lib/diagnosis-api";

const priorityOrder: Record<string,number> = {critical:0,high:1,medium:2,low:3};

function safeHttpUrl(value?:string|null) {
  if (!value) return null;
  try { const url=new URL(value); return ["http:","https:"].includes(url.protocol)?url.toString():null; } catch { return null; }
}

function workflow(f:Finding) {
  if (f.priority==="critical") return {label:"Fix first",detail:"Immediate technical correction",tone:"bg-red-50 text-red-800"};
  if (f.priority==="high") return {label:"Fix first",detail:"Validate in the next release",tone:"bg-red-50 text-red-800"};
  if (f.priority==="medium") return {label:"Validate next",detail:"Confirm with a repeatable check",tone:"bg-amber-50 text-amber-800"};
  return {label:"Review backlog",detail:"Approve after contextual review",tone:"bg-slate-100 text-slate-700"};
}

function CopyBlock({label,value}:{label:string;value:string}) {
  const [copied,setCopied]=useState(false);
  async function copy(){await navigator.clipboard.writeText(value);setCopied(true);setTimeout(()=>setCopied(false),1500);}
  return <div className="rounded-xl border border-blue-200 bg-blue-50 p-4"><div className="flex flex-wrap items-center justify-between gap-3"><p className="text-xs font-bold uppercase tracking-wide text-[#1755bd]">{label}</p><button type="button" onClick={copy} className="rounded-md border border-blue-200 bg-white px-3 py-1 text-xs font-semibold text-[#1755bd]">{copied?"Copied":"Copy"}</button></div><pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-white p-4 text-sm leading-6 text-[#292638]">{value}</pre></div>;
}

function SchemaComparison({e}:{e:Evidence}) {
  if (e.presentation_kind==="schema_identity_mismatch") {
    const names=[...String(e.observed_value||e.observed).matchAll(/'([^']+)'/g)].map(match=>match[1]);
    return <div className="grid gap-3 sm:grid-cols-2"><div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4"><p className="text-xs font-bold uppercase tracking-wide text-emerald-700">Visible resort page</p><p className="mt-1 font-semibold text-emerald-950">{names[0]||"Approved page identity"}</p></div><div className="rounded-xl border border-red-200 bg-red-50 p-4"><p className="text-xs font-bold uppercase tracking-wide text-red-700">Structured data currently says</p><p className="mt-1 font-semibold text-red-950">{names[1]||"Conflicting property identity"}</p></div></div>;
  }
  if (e.presentation_kind==="json_parse_error") return <div className="grid gap-3 sm:grid-cols-2"><div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4"><p className="text-xs font-bold uppercase tracking-wide text-emerald-700">Expected</p><p className="mt-1 font-semibold text-emerald-950">Valid machine-readable JSON</p></div><div className="rounded-xl border border-red-200 bg-red-50 p-4"><p className="text-xs font-bold uppercase tracking-wide text-red-700">Observed</p><p className="mt-1 font-semibold text-red-950">{e.observed_value||e.observed}</p></div></div>;
  return null;
}

function SerpTable({excerpt}:{excerpt:string}) {
  const lines=excerpt.split("\n").map(line=>line.trim()).filter(Boolean);
  const rows:Array<{result:string;url:string}> = [];
  for(let i=0;i<lines.length;i+=2) rows.push({result:lines[i],url:lines[i+1]||""});
  return <div className="overflow-hidden rounded-xl border bg-white"><div className="grid grid-cols-[3rem_1fr] bg-[#302663] px-4 py-2 text-xs font-semibold uppercase text-white"><span>Rank</span><span>Returned Google result</span></div>{rows.map((row,index)=><div key={`${row.result}-${index}`} className="grid grid-cols-[3rem_1fr] gap-2 border-t px-4 py-3"><span className="font-semibold text-[#667084]">{row.result.match(/^#(\d+)/)?.[1]||index+1}</span><div><p className="font-medium">{row.result.replace(/^#\d+\s*/,"")}</p>{safeHttpUrl(row.url)?<a className="mt-1 block break-all text-xs text-[#4d3caf] underline" href={row.url} target="_blank" rel="noreferrer">{new URL(row.url).hostname}</a>:null}</div></div>)}</div>;
}

function EvidenceCard({e,explanation}:{e:Evidence;explanation?:EvidenceExplanation}) {
  const [showImage,setShowImage]=useState(false);
  const observed=e.observed_value||e.observed;
  const normalize=(value?:string|null)=>String(value||"").replace(/\s+/g," ").trim().toLocaleLowerCase();
  const meaning=normalize(explanation?.plain_language)!==normalize(observed)?explanation?.plain_language:"";
  const excerpt=e.excerpt&&normalize(e.excerpt)!==normalize(observed)?e.excerpt:"";
  const measuredLength=e.presentation_kind==="metadata_length"?Number(observed.match(/\d+/)?.[0]||0):0;
  const sourceUrl=safeHttpUrl(e.source_url); const visualUrl=safeHttpUrl(e.visual_url);
  return <section className="mt-4 overflow-hidden rounded-2xl border border-[#d9d4e5] bg-[#f8f7fb]">
    <div className="flex flex-wrap items-center justify-between gap-2 border-b bg-[#eeebf7] px-5 py-4"><h4 className="font-semibold text-[#302663]">{e.title||"Observed proof"}</h4><span className="rounded-full bg-white px-2.5 py-1 text-[11px] font-semibold uppercase text-[#6852b2]">{(e.support_type||"evidence").replaceAll("_"," ")} · {e.confidence||"unrated"} confidence</span></div>
    <div className="space-y-4 p-5 text-sm leading-6">
      <SchemaComparison e={e}/>
      {measuredLength>0&&<div className="rounded-xl bg-white p-4"><div className="flex items-end justify-between gap-4"><div><p className="text-xs font-bold uppercase text-[#746d7e]">Current description</p><p className="mt-1 text-2xl font-semibold text-[#302663]">{measuredLength} characters</p></div><p className="text-right text-xs text-[#746d7e]">Editorial preview guideline<br/>70–160 characters</p></div><div className="mt-3 h-3 overflow-hidden rounded-full bg-[#e1deea]"><div className="h-full rounded-full bg-red-500" style={{width:`${Math.min(100,Math.max(4,measuredLength/10))}%`}}/></div></div>}
      {meaning&&<div><p className="text-xs font-semibold uppercase tracking-wide text-[#746d7e]">What this proves</p><p className="mt-1 text-base text-[#272330]">{meaning}</p></div>}
      <div><p className="text-xs font-semibold uppercase tracking-wide text-[#746d7e]">Observed on the tested page</p><p className="mt-1 whitespace-pre-wrap font-medium text-[#272330]">{observed}</p></div>
      {e.presentation_kind==="serp_sample"&&excerpt?<SerpTable excerpt={excerpt}/>:excerpt&&<div><p className="text-xs font-semibold uppercase tracking-wide text-[#746d7e]">Source excerpt</p><pre className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap break-words rounded-xl bg-white p-4 font-sans text-xs leading-6 text-[#514b59]">{excerpt}</pre></div>}
      {e.expected_value&&!["json_parse_error","schema_identity_mismatch"].includes(e.presentation_kind||"")&&<div><p className="text-xs font-semibold uppercase tracking-wide text-[#746d7e]">Decision rule</p><p className="mt-1 text-[#514b59]">{e.expected_value}</p></div>}
      {e.fix_example&&<CopyBlock label={e.fix_label||"Suggested answer - review before implementation"} value={e.fix_example}/>}
      {visualUrl&&!showImage&&<button type="button" onClick={()=>setShowImage(true)} className="rounded-lg border border-[#cfc8e2] bg-white px-4 py-2 font-semibold text-[#4d3caf]">Show affected image</button>}
      {visualUrl&&showImage&&<div><img src={visualUrl} alt="Affected website element shown as audit evidence" referrerPolicy="no-referrer" className="max-h-80 w-auto rounded-xl border object-contain"/><p className="mt-2 text-xs text-[#746d7e]">Loaded from the audited website after your request.</p></div>}
      <div className="rounded-lg bg-white px-4 py-3"><p className="text-xs font-semibold uppercase tracking-wide text-[#746d7e]">Where found</p><p className="mt-1">{e.location||"Selected resort page"}</p>{sourceUrl&&<a className="mt-2 inline-block font-semibold text-[#4d3caf] underline" href={sourceUrl} target="_blank" rel="noreferrer">Open source page</a>}</div>
      <details className="border-t pt-3 text-xs text-[#746d7e]"><summary className="cursor-pointer font-semibold">Technical evidence record</summary><p className="mt-2">Evidence ID: {e.id}</p><p>Method: {e.method}</p><p>Captured: {new Date(e.captured_at).toLocaleString()}</p>{e.verification&&<p className="mt-2"><b>Repeat this check:</b> {e.verification}</p>}</details>
    </div>
  </section>;
}

function ActionCase({finding,c,index,report}:{finding:Finding;c:Case;index:number;report:ManagementReport}) {
  const m=c.management; const labels=Object.fromEntries(report.cases.map(item=>[item.agent,item.agent_label]));
  const explanations=Object.fromEntries((m?.evidence_explanations||[]).map(item=>[item.evidence_id,item])); const stage=workflow(finding);
  return <section id={`finding-${finding.id}`} className="mt-7 scroll-mt-6 overflow-hidden rounded-[24px] border border-[#e0dde7] bg-white shadow-[0_14px_40px_rgba(39,32,66,.07)]">
    <header className="flex flex-wrap items-start justify-between gap-5 p-6 sm:p-7"><div className="flex min-w-0 gap-4"><span className="font-mono text-4xl text-[#3778f6]">{String(index+1).padStart(2,"0")}</span><div><p className="text-xs font-semibold uppercase tracking-[.15em] text-[#667084]">{finding.classification_label||finding.classification}</p><h2 className="mt-2 text-xl font-semibold sm:text-2xl">{finding.title}</h2><p className="mt-2 text-sm text-[#667084]">Primary agent: <b>{c.agent_label}</b>{finding.supporting_agents.length?` · Supported by ${finding.supporting_agents.map(a=>labels[a]||a).join(", ")}`:""}</p></div></div><span className={`rounded-full px-4 py-2 text-xs font-semibold ${stage.tone}`}>{stage.label}</span></header>
    <div className="grid gap-5 border-t bg-[#fbfafc] p-6 sm:grid-cols-2 sm:p-7"><div><p className="text-xs font-bold uppercase tracking-wide text-[#526077]">Why management should care</p><p className="mt-2 leading-7">{finding.business_relevance}</p></div><div><p className="text-xs font-bold uppercase tracking-wide text-[#1755bd]">Recommended action</p><p className="mt-2 leading-7">{finding.action}</p><p className="mt-2 text-xs text-[#667084]">Owner: {finding.owner} · {stage.detail}</p></div></div>
    <details open={index<2} className="group border-t"><summary className="cursor-pointer list-none px-6 py-4 font-semibold text-[#4d3caf] sm:px-7">View evidence and implementation guidance <span className="ml-2 inline-block group-open:rotate-90">›</span></summary><div className="space-y-6 border-t p-6 sm:p-7"><div><h3 className="text-xs font-bold uppercase tracking-wide text-[#1755bd]">Issue identified</h3><p className="mt-2 whitespace-pre-wrap text-lg leading-8">{finding.observation}</p></div>{finding.evidence_ids.map(id=>report.evidence[id]?<EvidenceCard key={id} e={report.evidence[id]} explanation={explanations[id]}/>:null)}<div className="rounded-xl border border-emerald-200 bg-emerald-50 p-5"><h3 className="text-xs font-bold uppercase tracking-wide text-emerald-800">Done when</h3><p className="mt-2 text-sm leading-6 text-emerald-950">{finding.completion_criteria}</p></div>{m?.limitation&&<p className="rounded-xl bg-[#fff7e8] p-4 text-sm text-[#6b5732]"><b>Evidence limit:</b> {m.limitation}</p>}<details className="border-t pt-4 text-sm text-[#686173]"><summary className="cursor-pointer font-semibold">Open agent record</summary><p className="mt-2">Execution: {c.status.replaceAll("_"," ")} · Internal quality gate: {(c.output_quality||"unrated").replaceAll("_"," ")}</p>{c.run_id&&<Link className="mt-2 inline-block underline" href={diagnosisAgentRunHref(c.agent,c.run_id)}>View full agent output</Link>}</details></div></details>
  </section>;
}

function Report({report}:{report:ManagementReport}) {
  const casesByAgent=Object.fromEntries(report.cases.map(c=>[c.agent,c])); const findings=[...report.findings].sort((a,b)=>(priorityOrder[a.priority]??9)-(priorityOrder[b.priority]??9));
  const counts=report.findings.reduce((all,f)=>({...all,[f.classification]:(all[f.classification]||0)+1}),{} as Record<string,number>);
  const contributionCounts=report.cases.reduce((all,c)=>{const key=c.output_quality==="rejected"?"rejected":c.contribution_role||"assessment";return {...all,[key]:(all[key]||0)+1};},{} as Record<string,number>);
  return <>
    <section className="mt-8 rounded-3xl bg-[#302663] p-7 text-white sm:p-9"><p className="text-xs uppercase tracking-[.2em] text-[#c8bff2]">Management diagnosis</p><h2 className="mt-3 text-3xl font-semibold">{report.identity?.branded_query||report.identity?.property_name||"Resort website review"}</h2><p className="mt-4 max-w-3xl leading-7 text-[#ece7ff]">{report.overview}</p><div className="mt-6 grid gap-3 sm:grid-cols-4"><div className="rounded-xl bg-white/10 p-4"><b className="text-2xl">{counts.confirmed||0}</b><p className="text-xs">Confirmed</p></div><div className="rounded-xl bg-white/10 p-4"><b className="text-2xl">{counts.review||0}</b><p className="text-xs">Review</p></div><div className="rounded-xl bg-white/10 p-4"><b className="text-2xl">{counts.opportunity||0}</b><p className="text-xs">Opportunity</p></div><div className="rounded-xl bg-white/10 p-4"><b className="text-2xl">{report.cases.length}</b><p className="text-xs">Agents recorded</p></div></div></section>
    <section className="mt-8 overflow-hidden rounded-2xl border bg-white"><div className="border-b p-6"><h2 className="text-2xl font-semibold">Prioritized action plan</h2><p className="mt-2 text-sm text-[#686173]">Select an issue to jump to its evidence and implementation guidance.</p></div><div className="divide-y">{findings.map((f,i)=>{const stage=workflow(f);return <a key={f.id} href={`#finding-${f.id}`} className="grid gap-2 p-5 hover:bg-[#faf9fc] sm:grid-cols-[2rem_1fr_auto]"><span className="font-mono text-[#3778f6]">{String(i+1).padStart(2,"0")}</span><span><b>{f.title}</b><span className="mt-1 block text-sm text-[#686173]">{f.action}</span></span><span className={`h-fit rounded-full px-3 py-1 text-xs font-semibold ${stage.tone}`}>{stage.label}</span></a>;})}</div></section>
    <section className="mt-10"><h2 className="text-2xl font-semibold">Evidence-backed action cases</h2><p className="mt-2 text-sm text-[#686173]">The first two confirmed issues are open. Expand the remaining cases when needed.</p>{findings.map((f,i)=>casesByAgent[f.primary_agent]?<ActionCase key={f.id} finding={f} c={casesByAgent[f.primary_agent]} index={i} report={report}/>:null)}</section>
    <section className="mt-12 overflow-hidden rounded-2xl border bg-white"><div className="border-b p-6"><h2 className="text-2xl font-semibold">Ten-agent contribution record</h2><p className="mt-2 text-sm text-[#686173]">{contributionCounts.primary||0} primary · {contributionCounts.supporting||0} supporting · {contributionCounts.assessment||0} assessment-only · {contributionCounts.rejected||0} rejected</p></div><div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="bg-[#302663] text-white"><tr><th className="p-4">Agent</th><th className="p-4">Contribution</th><th className="p-4">Outcome</th><th className="p-4">Record</th></tr></thead><tbody className="divide-y">{report.cases.map(c=><tr key={c.agent}><td className="p-4 font-semibold">{c.agent_label}</td><td className="p-4">{c.contribution_label||(c.output_quality==="rejected"?"Output rejected":c.contribution_role==="primary"?"Primary finding owner":c.contribution_role==="supporting"?"Supporting confirmation":"Assessment completed - no verified issue")}</td><td className="max-w-xl p-4 text-[#686173]">{c.management?.issue_identified||"No supported conclusion was retained."}</td><td className="p-4">{c.run_id?<Link className="font-semibold text-[#4d3caf] underline" href={diagnosisAgentRunHref(c.agent,c.run_id)}>Open</Link>:"Saved"}</td></tr>)}</tbody></table></div></section>
    <section className="mt-8 border-t pt-6"><h2 className="text-xl font-semibold">Scope and limitations</h2><ul className="mt-4 space-y-3 text-sm leading-7 text-[#686173]">{report.limitations.map((item,i)=><li key={i}>• {item}</li>)}</ul><details className="mt-5"><summary className="cursor-pointer font-semibold text-[#4d3caf]">Show {report.scope.length} inspected pages</summary>{report.scope.map(url=>safeHttpUrl(url)?<a key={url} className="mt-2 block break-all text-sm underline" href={url} target="_blank" rel="noreferrer">{url}</a>:null)}</details></section>
  </>;
}

const settledTaskStatuses = new Set(["complete", "failed", "needs_review", "cancelled", "skipped"]);

function StatusIcon({status}:{status:string}) {
  if (status === "complete") return <span className="grid h-8 w-8 place-items-center rounded-full bg-emerald-100 text-emerald-700" aria-hidden="true">✓</span>;
  if (status === "running") return <span className="relative grid h-8 w-8 place-items-center" aria-hidden="true"><span className="absolute h-8 w-8 animate-ping rounded-full bg-[#725ee8]/20"/><span className="relative h-3 w-3 rounded-full bg-[#5b45cf] shadow-[0_0_0_5px_rgba(91,69,207,.12)]"/></span>;
  if (status === "failed") return <span className="grid h-8 w-8 place-items-center rounded-full bg-red-100 font-bold text-red-700" aria-hidden="true">!</span>;
  if (status === "needs_review") return <span className="grid h-8 w-8 place-items-center rounded-full bg-amber-100 font-bold text-amber-700" aria-hidden="true">?</span>;
  return <span className="grid h-8 w-8 place-items-center rounded-full border border-[#ded9ec] bg-white" aria-hidden="true"><span className="h-2 w-2 rounded-full bg-[#c8c1dc]"/></span>;
}

function TaskCard({taskKey,status,error}:{taskKey:string;status:string;error?:string|null}) {
  const active=status==="running";
  const label=status.replaceAll("_"," ");
  const tone=status==="failed"?"text-red-700":status==="needs_review"?"text-amber-700":status==="complete"?"text-emerald-700":active?"text-[#5641c5]":"text-[#817a90]";
  return <li className={`relative flex min-h-24 items-center gap-4 rounded-2xl border p-4 transition ${active?"border-[#8b78ed] bg-[#f5f2ff] shadow-[0_10px_30px_rgba(76,56,170,.12)]":"border-[#e5e1ea] bg-white"}`}>
    {active&&<span className="absolute inset-y-3 left-0 w-1 rounded-r-full bg-[#6048da]"/>}
    <StatusIcon status={status}/><div className="min-w-0"><p className="font-semibold text-[#282334]">{diagnosisLabels[taskKey]||taskKey}</p><p className={`mt-1 text-xs font-semibold capitalize ${tone}`}>{active?"Working now":label}</p>{error&&<p className="mt-2 line-clamp-2 text-xs leading-5 text-red-700" title={error}>{error}</p>}</div>
  </li>;
}

function InitialLoadingScreen() {
  return <section className="mt-8 overflow-hidden rounded-[28px] border border-[#e1ddeb] bg-white shadow-[0_24px_70px_rgba(37,28,73,.08)]" aria-live="polite">
    <div className="bg-[#33276d] px-6 py-9 text-white sm:px-9"><div className="flex items-center gap-4"><span className="relative grid h-12 w-12 place-items-center rounded-2xl bg-white/10"><span className="absolute h-8 w-8 animate-ping rounded-full bg-white/10"/><span className="h-3 w-3 rounded-full bg-[#a998ff]"/></span><div><p className="text-xs font-semibold uppercase tracking-[.2em] text-[#c9c0f3]">Connecting to diagnosis</p><h2 className="mt-1 text-2xl font-semibold">Loading saved progress…</h2></div></div></div>
    <div className="space-y-4 p-6 sm:p-9"><div className="h-3 w-full animate-pulse rounded-full bg-[#ece9f2]"/><div className="grid gap-3 sm:grid-cols-3">{[0,1,2].map(item=><div key={item} className="h-24 animate-pulse rounded-2xl bg-[#f2f0f6]"/>)}</div><p className="text-sm text-[#6e6878]">Restoring completed evidence and the current specialist status.</p></div>
  </section>;
}

function DiagnosisProgress({run}:{run:Diagnosis}) {
  const entries=Object.entries(run.tasks);
  const settled=entries.filter(([,task])=>settledTaskStatuses.has(task.status)).length;
  const completed=entries.filter(([,task])=>task.status==="complete").length;
  const attention=entries.filter(([,task])=>["failed","needs_review"].includes(task.status)).length;
  const active=entries.find(([,task])=>task.status==="running");
  const percent=Math.round((settled/Math.max(entries.length,1))*100);
  const phases=[
    {number:"01",title:"Collect page evidence",detail:"Capture the resort page and supporting pages once.",keys:["capture"]},
    {number:"02",title:"Run specialist checks",detail:"Ten agents review the same saved evidence from their areas of expertise.",keys:entries.map(([key])=>key).filter(key=>!["capture","report"].includes(key))},
    {number:"03",title:"Build management report",detail:"Merge verified findings, recommendations and agent contributions.",keys:["report"]},
  ];
  return <section className="mt-8 overflow-hidden rounded-[28px] border border-[#ddd8e9] bg-white shadow-[0_24px_70px_rgba(37,28,73,.09)]" aria-live="polite">
    <div className="relative overflow-hidden bg-[#33276d] px-6 py-8 text-white sm:px-9 sm:py-10"><div className="absolute -right-20 -top-24 h-64 w-64 rounded-full bg-[#7e68ee]/25 blur-2xl"/><div className="relative flex flex-wrap items-end justify-between gap-6"><div><p className="text-xs font-semibold uppercase tracking-[.2em] text-[#c9c0f3]">Live diagnosis progress</p><h2 className="mt-2 text-2xl font-semibold sm:text-3xl">{active?`${diagnosisLabels[active[0]]} is working` : settled===entries.length?"Specialist checks finished":"Preparing the next specialist"}</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-[#e7e2ff]">Results are saved after every task. You can leave this page and return without losing completed work.</p></div><div className="text-right"><p className="text-4xl font-semibold">{percent}%</p><p className="mt-1 text-xs text-[#c9c0f3]">{settled} of {entries.length} tasks settled</p></div></div><div className="relative mt-7 h-2 overflow-hidden rounded-full bg-white/15"><div className="h-full rounded-full bg-gradient-to-r from-[#8f7cff] to-[#b7a9ff] transition-[width] duration-700" style={{width:`${percent}%`}}/></div><div className="relative mt-5 flex flex-wrap gap-5 text-xs text-[#ddd7fa]"><span><b className="text-white">{completed}</b> completed</span><span><b className="text-white">{entries.length-settled}</b> remaining</span>{attention>0&&<span className="text-amber-200"><b>{attention}</b> retained for review</span>}</div></div>
    <div className="space-y-8 p-6 sm:p-9">{phases.map(phase=>{const phaseTasks=phase.keys.filter(key=>run.tasks[key]);const phaseDone=phaseTasks.length>0&&phaseTasks.every(key=>settledTaskStatuses.has(run.tasks[key].status));const phaseActive=phaseTasks.some(key=>run.tasks[key].status==="running");return <section key={phase.number}><div className="mb-4 flex items-start gap-4"><span className={`grid h-9 w-9 shrink-0 place-items-center rounded-xl text-xs font-bold ${phaseDone?"bg-emerald-100 text-emerald-700":phaseActive?"bg-[#5b45cf] text-white":"bg-[#efedf4] text-[#817a90]"}`}>{phaseDone?"✓":phase.number}</span><div><h3 className="font-semibold text-[#282334]">{phase.title}</h3><p className="mt-1 text-sm text-[#706979]">{phase.detail}</p></div></div><ol className={`grid gap-3 ${phaseTasks.length>2?"sm:grid-cols-2 lg:grid-cols-3":""}`}>{phaseTasks.map(key=><TaskCard key={key} taskKey={key} status={run.tasks[key].status} error={run.tasks[key].error}/>)}</ol></section>;})}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-[#e7e3ee] bg-[#faf9fc] p-4"><p className="text-sm text-[#615a6c]"><b className="text-[#282334]">Safe to close:</b> progress is stored after every completed specialist.</p><span className="flex items-center gap-2 text-xs font-semibold text-[#6654bd]"><span className="h-2 w-2 animate-pulse rounded-full bg-[#6654bd]"/>Updates automatically</span></div>
    </div>
  </section>;
}

export function DiagnosisRun({id}:{id:string}) {
  const [run,setRun]=useState<Diagnosis|null>(null); const [error,setError]=useState(""); const [busy,setBusy]=useState(false); const [version,setVersion]=useState(0);
  useEffect(()=>{let stopped=false;let timer:ReturnType<typeof setTimeout>;let inFlight=0;async function poll(){try{const value=await diagnosisRequest<Diagnosis>(`/${id}`);if(stopped)return;setRun(value);if(!["complete","partial","cancelled"].includes(value.status)&&inFlight<1){inFlight++;void diagnosisRequest<Diagnosis>(`/${id}/advance`,{},"POST").catch(e=>{if(!stopped)setError(e.message);}).finally(()=>{inFlight--;});}if(["complete","partial","cancelled"].includes(value.status))return;}catch(e){if(!stopped)setError(e instanceof Error?e.message:"Connection interrupted; retrying.");}if(!stopped)timer=setTimeout(poll,3000);}void poll();return()=>{stopped=true;clearTimeout(timer);};},[id,version]);
  async function action(name:string){try{setBusy(true);setError("");const value=await diagnosisRequest<Diagnosis>(`/${id}/${name}`,{},"POST");setRun(value);setVersion(v=>v+1);}catch(e){setError(e instanceof Error?e.message:"Action failed");}finally{setBusy(false);}}
  async function download(){try{const response=await fetch(`${diagnosisBase}/${id}/report.pdf`,{credentials:"include"});if(!response.ok)throw new Error("PDF could not be generated. Please retry.");const url=URL.createObjectURL(await response.blob());const a=document.createElement("a");a.href=url;a.download=`resort-diagnosis-${id}.pdf`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){setError(e instanceof Error?e.message:"Download failed");}}
  return <main className="mx-auto max-w-6xl px-5 py-8 sm:px-8 sm:py-12"><Link href="/diagnosis" className="inline-flex items-center gap-2 text-sm font-semibold text-[#6552aa] transition hover:text-[#3f318f]">← Website Diagnosis</Link><header className="mt-6 rounded-[28px] border border-[#e2deea] bg-white p-6 shadow-[0_18px_55px_rgba(37,28,73,.06)] sm:p-8"><div className="flex flex-wrap items-start justify-between gap-5"><div className="min-w-0"><p className="text-xs font-semibold uppercase tracking-[.2em] text-[#6552aa]">Resort management review</p><h1 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">{run?.report?.identity?.branded_query||run?.report?.identity?.property_name||"Diagnosing your resort page"}</h1><p className="mt-3 max-w-3xl break-all text-sm text-[#686173]">{run?.request.page_url||"Restoring the saved diagnosis…"}</p>{run?.report&&<p className="mt-2 text-xs text-gray-500">Evidence captured {run.report.captured_at?new Date(run.report.captured_at).toLocaleString():"time unavailable"} · Report version {run.report.version}</p>}</div><span className={`rounded-full px-4 py-2 text-xs font-bold uppercase tracking-wide ${run?.status==="complete"?"bg-emerald-100 text-emerald-800":run?.status==="partial"?"bg-amber-100 text-amber-800":"bg-[#eeeaff] text-[#5540bd]"}`}>{run?.status?.replaceAll("_"," ")||"Loading"}</span></div><div className="mt-6 flex flex-wrap gap-3">{run?.report&&<button onClick={download} className="rounded-xl bg-[#4839ac] px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-[#3d2f99]">Download management PDF</button>}{run?.report&&<button disabled={busy} onClick={()=>action("refresh-report")} className="rounded-xl border border-[#d8d3e3] bg-white px-5 py-3 text-sm font-semibold transition hover:bg-[#faf9fc] disabled:opacity-50">{busy?"Updating…":"Refresh management wording"}</button>}{run?.report&&<button disabled={busy} onClick={()=>action("rerun-all")} className="rounded-xl border border-[#d8d3e3] bg-white px-5 py-3 text-sm font-semibold transition hover:bg-[#faf9fc] disabled:opacity-50">Run fresh evidence check</button>}{run&&["running","queued"].includes(run.status)&&<button onClick={()=>action("cancel")} className="rounded-xl border border-[#e1dce8] px-5 py-3 text-sm font-semibold text-[#706979]">Cancel remaining work</button>}</div></header>{error&&<p role="alert" className="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error} <button className="font-semibold underline" onClick={()=>{setError("");setVersion(v=>v+1);}}>Reconnect</button></p>}{run?.report&&run.report.version<5&&<section className="mt-6 rounded-2xl border border-amber-300 bg-amber-50 p-6"><h2 className="text-xl font-semibold">Rerun required before management use</h2><p className="mt-2 text-sm">This saved report predates the current evidence-specific management format.</p><button disabled={busy} onClick={()=>action("upgrade")} className="mt-4 rounded-xl bg-amber-900 px-5 py-3 text-sm font-semibold text-white">Upgrade and rerun all ten agents</button></section>}{!run&&<InitialLoadingScreen/>}{run&&!run.report&&<DiagnosisProgress run={run}/>} {run?.report&&run.report.version>=5&&<Report report={run.report}/>}</main>;
}
