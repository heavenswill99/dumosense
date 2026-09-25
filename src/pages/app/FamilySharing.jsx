import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, apiError } from "@/lib/api";
import { CoreMark } from "@/components/CoreMark";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { Users, Copy, Trash2, Eye, Plus, ShieldCheck } from "lucide-react";

const SCOPE_LABELS = {
  mindguard: "MindGuard pattern",
  changes: "Recent changes",
  reserve: "Health Reserve preparedness",
};

function StatusBadge({ status }) {
  const map = {
    pending: { label: "Awaiting", cls: "bg-secondary text-muted-foreground" },
    active: { label: "Active", cls: "bg-status-success/15 text-status-success" },
    revoked: { label: "Revoked", cls: "bg-destructive/10 text-destructive" },
  };
  const s = map[status] || map.pending;
  return <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${s.cls}`}>{s.label}</span>;
}

function SharedSummary({ data }) {
  const { scopes = {} } = data;
  return (
    <div className="mt-4 space-y-3" data-testid="shared-summary">
      {scopes.mindguard && data.mindguard && (
        <div className="rounded-2xl border border-border bg-background-secondary/60 p-4">
          <div className="flex items-center gap-2">
            <CoreMark state="learning" size={22} />
            <p className="font-display text-sm font-medium text-foreground">MindGuard pattern</p>
          </div>
          <p className="mt-2 text-sm text-foreground">{data.mindguard.message}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Pattern state: <span className="capitalize">{data.mindguard.pattern_state.replace(/_/g, " ")}</span>
            {" · "}{data.mindguard.total} observation{data.mindguard.total === 1 ? "" : "s"}
          </p>
        </div>
      )}
      {scopes.changes && data.change && (
        <div className="rounded-2xl border border-border bg-background-secondary/60 p-4">
          <div className="flex items-center gap-2">
            <CoreMark state={data.change.state === "meaningful_change" ? "change" : "static"} size={22} />
            <p className="font-display text-sm font-medium text-foreground">Recent changes</p>
          </div>
          <p className="mt-2 text-sm text-foreground">{data.change.title || "No recent change identified."}</p>
          {data.change.body && <p className="mt-1 text-xs text-muted-foreground">{data.change.body}</p>}
        </div>
      )}
      {scopes.reserve && data.reserve && (
        <div className="rounded-2xl border border-border bg-background-secondary/60 p-4">
          <div className="flex items-center gap-2">
            <CoreMark state="intelligence" size={22} />
            <p className="font-display text-sm font-medium text-foreground">Health Reserve preparedness</p>
          </div>
          {data.reserve.assessed ? (
            <>
              <p className="mt-2 text-sm text-foreground">{data.reserve.message}</p>
              <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-secondary">
                <div className="h-full rounded-full bg-rose" style={{ width: `${data.reserve.progress}%` }} />
              </div>
              <p className="mt-1.5 text-xs text-muted-foreground">{data.reserve.progress}% towards their preparedness target.</p>
            </>
          ) : (
            <p className="mt-2 text-sm text-muted-foreground">They haven't completed a preparedness assessment yet.</p>
          )}
        </div>
      )}
    </div>
  );
}

function ShareRow({ share, onChanged }) {
  const [scopes, setScopes] = useState(share.scopes);
  const revoked = share.status === "revoked";

  const copy = () => {
    navigator.clipboard?.writeText(share.code);
    toast.success("Invite code copied.");
  };

  const setScope = async (key, val) => {
    const next = { ...scopes, [key]: val };
    setScopes(next);
    try {
      await api.post(`/family/shares/${share.share_id}/scopes`, next);
      toast.success("Sharing updated.");
    } catch {
      setScopes(scopes);
      toast.error("Could not update sharing.");
    }
  };

  const revoke = async () => {
    try {
      await api.post(`/family/shares/${share.share_id}/revoke`);
      toast.success("Access revoked.");
      onChanged();
    } catch {
      toast.error("Could not revoke access.");
    }
  };

  return (
    <div data-testid={`share-${share.share_id}`}
      className={`rounded-3xl border p-5 ${revoked ? "border-border bg-secondary/30 opacity-70" : "border-border bg-card"}`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-display text-base font-medium text-foreground">
            {share.member_name || share.label || "Family invite"}
          </p>
          <p className="text-xs text-muted-foreground">
            {share.member_email || (share.status === "pending" ? "Not yet accepted" : "")}
          </p>
        </div>
        <StatusBadge status={share.status} />
      </div>

      {!revoked && (
        <div className="mt-4 flex items-center gap-2">
          <span data-testid="share-code"
            className="rounded-xl border border-dashed border-input bg-background-secondary px-3 py-2 font-mono text-sm tracking-widest text-foreground">
            {share.code}
          </span>
          <Button variant="outline" size="sm" onClick={copy} data-testid="copy-code"
            className="rounded-full border-border bg-transparent hover:bg-surface-hover">
            <Copy className="mr-1.5 h-3.5 w-3.5" /> Copy
          </Button>
        </div>
      )}

      {!revoked && (
        <div className="mt-4 space-y-2.5 border-t border-border pt-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">What they can see</p>
          {Object.keys(SCOPE_LABELS).map((k) => (
            <div key={k} className="flex items-center justify-between">
              <span className="text-sm text-foreground">{SCOPE_LABELS[k]}</span>
              <Switch checked={!!scopes[k]} onCheckedChange={(v) => setScope(k, v)}
                data-testid={`scope-${k}-${share.share_id}`} aria-label={SCOPE_LABELS[k]} />
            </div>
          ))}
          <div className="pt-2">
            <Button variant="ghost" size="sm" onClick={revoke} data-testid="revoke-share"
              className="rounded-full text-destructive hover:bg-destructive/10">
              <Trash2 className="mr-1.5 h-3.5 w-3.5" /> Revoke access
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function FamilySharing() {
  const navigate = useNavigate();
  const [owner, setOwner] = useState(null);
  const [sharedWithMe, setSharedWithMe] = useState(null);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [openView, setOpenView] = useState(null);
  const [viewData, setViewData] = useState(null);

  const loadOwner = () => api.get("/family/shares").then(({ data }) => setOwner(data));
  const loadShared = () => api.get("/family/shared-with-me").then(({ data }) => setSharedWithMe(data.shares));

  useEffect(() => { loadOwner(); loadShared(); }, []);

  const createInvite = async () => {
    setBusy(true);
    try {
      await api.post("/family/invite", {});
      toast.success("Invite created — share the code.");
      loadOwner();
    } catch (e) {
      toast.error(apiError(e.response?.data?.detail) || "Could not create invite.");
    } finally {
      setBusy(false);
    }
  };

  const accept = async () => {
    if (!code.trim()) return;
    setBusy(true);
    try {
      const { data } = await api.post("/family/accept", { code });
      toast.success(`You're now connected to ${data.owner_name}.`);
      setCode("");
      loadShared();
    } catch (e) {
      toast.error(apiError(e.response?.data?.detail) || "Could not accept that code.");
    } finally {
      setBusy(false);
    }
  };

  const openSharedView = async (id) => {
    if (openView === id) { setOpenView(null); return; }
    setOpenView(id);
    setViewData(null);
    try {
      const { data } = await api.get(`/family/view/${id}`);
      setViewData(data);
    } catch {
      toast.error("Could not open that shared view.");
      setOpenView(null);
    }
  };

  if (!owner || !sharedWithMe) return <Skeleton className="h-96 w-full rounded-3xl" />;

  return (
    <div className="space-y-8">
      {/* Owner: invite people */}
      <section>
        <div className="mb-3 flex items-center gap-2">
          <Users className="h-5 w-5 text-primary" />
          <h2 className="font-display text-lg font-medium text-foreground">People you share with</h2>
        </div>

        {owner.is_family ? (
          <>
            <div className="rounded-3xl border border-border bg-secondary/40 p-4 text-sm text-muted-foreground">
              Invite a relative or caregiver into a calm, read-only view of your health intelligence.
              You choose what they see and can revoke access anytime.
            </div>
            <Button onClick={createInvite} disabled={busy} data-testid="family-create-invite"
              className="mt-4 h-11 rounded-full bg-primary px-6 text-primary-foreground hover:opacity-90">
              <Plus className="mr-1.5 h-4 w-4" /> Create an invite
            </Button>

            <div className="mt-5 space-y-4">
              {owner.shares.length === 0 && (
                <p className="text-sm text-muted-foreground">No invites yet. Create one to get started.</p>
              )}
              {owner.shares.map((s) => (
                <ShareRow key={s.share_id} share={s} onChanged={loadOwner} />
              ))}
            </div>
          </>
        ) : (
          <div data-testid="family-upsell" className="rounded-3xl border border-border bg-card p-6">
            <div className="flex items-center gap-3">
              <CoreMark state="intelligence" size={28} />
              <p className="font-display text-base font-medium text-foreground">Sharing is part of the Family plan</p>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              Upgrade to Family to invite relatives and caregivers into a shared, permissioned view.
            </p>
            <Button variant="outline" onClick={() => navigate("/app/membership")} data-testid="family-upgrade"
              className="mt-4 rounded-full border-border bg-transparent hover:bg-surface-hover">
              View Family plan
            </Button>
          </div>
        )}
      </section>

      {/* Invitee: accept + view */}
      <section>
        <div className="mb-3 flex items-center gap-2">
          <ShieldCheck className="h-5 w-5 text-primary" />
          <h2 className="font-display text-lg font-medium text-foreground">Shared with you</h2>
        </div>

        <div className="rounded-3xl border border-border bg-card p-5">
          <p className="text-sm text-muted-foreground">Have an invite code from a family member? Enter it here.</p>
          <div className="mt-3 flex gap-2">
            <Input value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} placeholder="INVITE CODE"
              data-testid="accept-code-input" maxLength={12}
              className="h-11 rounded-xl border-input bg-background-secondary font-mono tracking-widest" />
            <Button onClick={accept} disabled={busy || !code.trim()} data-testid="accept-code-submit"
              className="h-11 rounded-full bg-primary px-6 text-primary-foreground hover:opacity-90">
              Accept
            </Button>
          </div>
        </div>

        <div className="mt-5 space-y-4">
          {sharedWithMe.length === 0 && (
            <p className="text-sm text-muted-foreground">No one is sharing with you yet.</p>
          )}
          {sharedWithMe.map((s) => (
            <div key={s.share_id} data-testid={`shared-with-me-${s.share_id}`}
              className="rounded-3xl border border-border bg-card p-5">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-secondary font-display text-primary">
                    {s.owner_name?.[0]?.toUpperCase() || "F"}
                  </div>
                  <div>
                    <p className="font-display text-base font-medium text-foreground">{s.owner_name}</p>
                    <p className="text-xs text-muted-foreground">Read-only shared view</p>
                  </div>
                </div>
                <Button variant="outline" onClick={() => openSharedView(s.share_id)} data-testid="view-share"
                  className="rounded-full border-border bg-transparent hover:bg-surface-hover">
                  <Eye className="mr-1.5 h-4 w-4" /> {openView === s.share_id ? "Hide" : "View"}
                </Button>
              </div>
              {openView === s.share_id && (
                viewData ? <SharedSummary data={viewData} /> : <Skeleton className="mt-4 h-40 w-full rounded-2xl" />
              )}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
