#!/usr/bin/env python3
"""Deterministic checks for the Project/Task lifecycle."""
import argparse, hashlib, json, os, re, shutil, subprocess, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path

class Error(RuntimeError): pass

def run(root, *args):
    p = subprocess.run(args, cwd=root, text=True, capture_output=True)
    if p.returncode: raise Error(p.stderr.strip() or p.stdout.strip())
    return p.stdout.strip()

def root_at(raw):
    root = Path(raw).resolve()
    if not (root/"STATE.md").is_file() or not (root/"tasks/_template").is_dir():
        raise Error("not a Project root")
    return root

def task_at(root, name):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        raise Error("Task name must use lowercase kebab-case")
    return root/"tasks"/name

def section(text, name):
    m = re.search(r"(?ms)^## "+re.escape(name)+r"\s*\n(.*?)(?=^## |\Z)", text)
    if not m: raise Error("missing section: "+name)
    return m.group(1).strip()

def replace(text, name, body):
    p = re.compile(r"(?ms)(^## "+re.escape(name)+r"\s*\n).*?(?=^## |\Z)")
    if not p.search(text): raise Error("missing section: "+name)
    return p.sub(lambda m:m.group(1)+"\n"+body.strip()+"\n\n", text).rstrip()+"\n"

def scalar(text, name):
    lines=[x.strip() for x in section(text,name).splitlines() if x.strip() and not x.startswith("허용값")]
    if not lines: raise Error("empty section: "+name)
    return lines[0]

def table(body):
    out=[]
    for line in body.splitlines():
        if line.strip().startswith("|"):
            cells=[x.strip() for x in line.strip().strip("|").split("|")]
            if not all(re.fullmatch(r":?-+:?",x) for x in cells): out.append(cells)
    return out[1:] if out else []

def state_rows(root): return table(section((root/"STATE.md").read_text(),"Current Tasks"))

def write_state(root, rows):
    path=root/"STATE.md"; text=path.read_text()
    intro=section(text,"Current Tasks").split("| Task |",1)[0].rstrip()
    body=intro+"\n\n| Task | Status | Path | Note |\n| --- | --- | --- | --- |\n"
    body+="".join("| "+" | ".join(row)+" |\n" for row in rows)
    path.write_text(replace(text,"Current Tasks",body))

def set_state(root,name,old,new):
    rows=state_rows(root); found=[r for r in rows if len(r)>=4 and r[0]==name]
    if len(found)!=1 or found[0][1]!=old: raise Error("Project STATE must be "+old)
    found[0][1]=new; write_state(root,rows)

def source_at(root, raw, allowed):
    path=(root/raw).resolve()
    try: relative=path.relative_to(root)
    except ValueError as e: raise Error("source is outside Project: "+raw) from e
    if not any(relative==Path(base) or Path(base) in relative.parents for base in allowed):
        raise Error("source is outside allowed roots: "+raw)
    if not path.exists():raise Error("source does not exist: "+raw)
    return path

def destination(raw):
    path=Path(raw)
    if path.is_absolute() or ".." in path.parts:raise Error("invalid Task destination: "+raw)
    return path

def create(a):
    root=root_at(a.root); task=task_at(root,a.name)
    if task.exists() or any(r and r[0]==a.name for r in state_rows(root)): raise Error("Task already exists")
    code=[(source_at(root,s,("src","tools","project/src","project/tools")),destination(d),s,d) for s,d in (a.copy_code or [])]
    data=[(source_at(root,s,("data","project/data")),destination(d),s,d) for s,d in (a.link_data or [])]
    stage=Path(tempfile.mkdtemp(prefix="."+a.name+"-",dir=root/"tasks")); old=(root/"STATE.md").read_text()
    try:
        shutil.copytree(root/"tasks/_template",stage,dirs_exist_ok=True)
        ignore=shutil.ignore_patterns(".git",".codex",".env",".env.*","*.pem","*.key","__pycache__",".venv","venv","node_modules")
        for source,dest,_,_ in code:
            target=stage/"scripts"/dest
            if source.is_dir():shutil.copytree(source,target,ignore=ignore)
            else:target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        for source,dest,_,_ in data:
            target=stage/"data"/dest;target.parent.mkdir(parents=True,exist_ok=True)
            target.symlink_to(os.path.relpath(source,target.parent))
        path=stage/"STATUS.md"; path.write_text(replace(path.read_text(),"Final Goal",a.goal))
        doc=stage/"TASK.md";text=doc.read_text()
        inputs=["| Project Source | Task Snapshot |","| --- | --- |"]+(["| %s | scripts/%s |"%(s,d) for _,_,s,d in code] or ["| None | None |"])
        links=["| Project Data | Task Link |","| --- | --- |"]+(["| %s | data/%s |"%(s,d) for _,_,s,d in data] or ["| None | None |"])
        text=replace(text,"Inputs","\n".join(inputs));doc.write_text(replace(text,"Data","\n".join(links)))
        stage.rename(task); rows=state_rows(root); rows.append([a.name,"todo","tasks/"+a.name,""]); write_state(root,rows)
    except Exception:
        (root/"STATE.md").write_text(old); shutil.rmtree(stage,ignore_errors=True); shutil.rmtree(task,ignore_errors=True); raise
    print("created tasks/"+a.name)

def validate(root,name,phase):
    task=task_at(root,name); errors=[]
    for x in ("AGENTS.md","TASK.md","STATUS.md","REPORT.md",".codex/config.toml"):
        if not (task/x).is_file(): errors.append("missing "+x)
    for x in ("scripts","data","docs/research","docs/notes","output"):
        if not (task/x).is_dir(): errors.append("missing "+x+"/")
    if errors:return errors
    config=(task/".codex/config.toml").read_text()
    for key,value in (("sandbox_mode","danger-full-access"),("approval_policy","never")):
        if len(re.findall(r"(?m)^"+key+r"\s*=",config))!=1 or not re.search(r'(?m)^'+key+r'\s*=\s*"'+value+r'"\s*$',config):
            errors.append("invalid config: "+key)
    status=(task/"STATUS.md").read_text(); doc=(task/"TASK.md").read_text()
    try:
        current=scalar(status,"Status")
        if current not in ("todo","doing","completed","stopped"):errors.append("invalid Task status")
        if scalar(status,"Final Goal")=="TBD":errors.append("Final Goal is incomplete")
        work=table(section(status,"Work Plan"))
        if not work:errors.append("Work Plan is empty")
        if any(len(r)!=2 or r[1] not in ("todo","doing","completed") for r in work):errors.append("invalid Work Plan")
        scalar(status,"Current Work")
    except Error as e:errors.append(str(e));current=""
    if len([r for r in state_rows(root) if r and r[0]==name])!=1:errors.append("STATE row is missing or duplicated")
    if phase in ("ready","completed"):
        for h in ("Scope","Workflow","Outputs","Completion Criteria"):
            try:
                if "TBD" in section(doc,h):errors.append(h+" is incomplete")
            except Error as e:errors.append(str(e))
    if phase=="ready" and current!="todo":errors.append("ready Task must be todo")
    if phase=="completed":
        if current!="completed":errors.append("completed Task must be completed")
        report=(task/"REPORT.md").read_text()
        for h in ("Outcome","Summary","Final Goal and Result","Findings","Work and Validation","Relevant Files","Limitations","Project Follow-up"):
            try:
                if "TBD" in section(report,h):errors.append("REPORT "+h+" is incomplete")
            except Error as e:errors.append(str(e))
    return errors

def require(root,name,phase):
    errors=validate(root,name,phase)
    if errors:raise Error("\n".join("- "+x for x in errors))

def validate_cmd(a):
    root=root_at(a.root);require(root,a.name,a.phase);print(a.name+": "+a.phase+" validation passed")

def activate(a):
    root=root_at(a.root);task=task_at(root,a.name);require(root,a.name,"ready")
    sp=task/"STATUS.md"; old_s=sp.read_text(); old_p=(root/"STATE.md").read_text()
    try:
        sp.write_text(replace(old_s,"Status","doing\n\n허용값은 todo, doing, completed, stopped다."));set_state(root,a.name,"todo","doing")
    except Exception:
        sp.write_text(old_s);(root/"STATE.md").write_text(old_p);raise
    print("activated; commit before baseline")

def hashes(task):
    out={}
    for link in sorted(x for x in (task/"data").rglob("*") if x.is_symlink()):
        target=link.resolve(); files=[target] if target.is_file() else sorted(x for x in target.rglob("*") if x.is_file()) if target.exists() else []
        if not files:out[str(link.relative_to(task))]="MISSING"
        for f in files:out[str(link.relative_to(task))+":"+f.name]=hashlib.sha256(f.read_bytes()).hexdigest()
    return out

def meta(root,name):
    gd=Path(run(root,"git","rev-parse","--git-dir"));gd=gd if gd.is_absolute() else root/gd
    return gd/"harness/tasks"/(name+".json")

def baseline(a):
    root=root_at(a.root);task=task_at(root,a.name);require(root,a.name,"created")
    if scalar((task/"STATUS.md").read_text(),"Status")!="doing" or not any(r[0]==a.name and r[1]=="doing" for r in state_rows(root)):raise Error("Task and Project must be doing")
    if run(root,"git","status","--porcelain"):raise Error("Git worktree must be clean")
    commit=run(root,"git","rev-parse","HEAD");path=meta(root,a.name);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps({"commit":commit,"linked_data":hashes(task)},indent=2,sort_keys=True)+"\n")
    run(root,"git","update-ref","refs/harness/tasks/"+a.name,commit);print("baseline "+commit)

def audit_errors(root,name):
    task=task_at(root,name);path=meta(root,name)
    if not path.is_file():return ["missing baseline"]
    saved=json.loads(path.read_text()); changed=run(root,"git","diff","--name-only",saved["commit"],"--").splitlines()
    changed+=run(root,"git","ls-files","--others","--exclude-standard").splitlines();prefix="tasks/"+name+"/"
    errors=["unexpected Project change: "+x for x in sorted(set(changed)) if x and not x.startswith(prefix)]
    now=hashes(task);errors+=["linked data changed: "+x for x in sorted(set(saved["linked_data"])|set(now)) if saved["linked_data"].get(x)!=now.get(x)]
    return errors

def audit(a):
    errors=audit_errors(root_at(a.root),a.name)
    if errors:raise Error("\n".join("- "+x for x in errors))
    print(a.name+": audit passed")

def status_cmd(a):
    root=root_at(a.root);items=[]
    for r in state_rows(root):
        task=root/r[2];items.append({"task":r[0],"project":r[1],"task_status":scalar((task/"STATUS.md").read_text(),"Status") if task.is_dir() else "missing"})
    if a.json:print(json.dumps(items,indent=2));return
    for x in items:
        alert=" [return to Project session]" if x["project"]=="doing" and x["task_status"]=="completed" else ""
        print("%(task)s: Project=%(project)s, Task=%(task_status)s"%x+alert)

def acknowledge(a):
    root=root_at(a.root);require(root,a.name,"completed");errors=audit_errors(root,a.name)
    if errors:raise Error("\n".join("- "+x for x in errors))
    set_state(root,a.name,"doing","completed");history=root/"docs/history";history.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M");path=history/(stamp+"-completed-"+a.name+".md")
    path.write_text("# Task completed: %s\n\n- Task: tasks/%s\n- Report: tasks/%s/REPORT.md\n- Promotion: not evaluated\n"%(a.name,a.name,a.name))
    print("acknowledged "+a.name)

def parser():
    p=argparse.ArgumentParser();p.add_argument("--root",default=".");task=p.add_subparsers(required=True).add_parser("task");subs=task.add_subparsers(required=True)
    x=subs.add_parser("create");x.add_argument("name");x.add_argument("--goal",required=True)
    x.add_argument("--copy-code",nargs=2,action="append",metavar=("SOURCE","DEST"))
    x.add_argument("--link-data",nargs=2,action="append",metavar=("SOURCE","NAME"));x.set_defaults(fn=create)
    x=subs.add_parser("validate");x.add_argument("name");x.add_argument("--phase",choices=("created","ready","completed"),default="created");x.set_defaults(fn=validate_cmd)
    for name,fn in (("activate",activate),("baseline",baseline),("audit",audit),("acknowledge",acknowledge)):
        x=subs.add_parser(name);x.add_argument("name");x.set_defaults(fn=fn)
    x=subs.add_parser("status");x.add_argument("--json",action="store_true");x.set_defaults(fn=status_cmd);return p

def main():
    try:a=parser().parse_args();a.fn(a);return 0
    except (Error,OSError,json.JSONDecodeError) as e:print("error: "+str(e),file=sys.stderr);return 1
if __name__=="__main__":raise SystemExit(main())
