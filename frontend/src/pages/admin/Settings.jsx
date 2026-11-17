import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Send, Trash2 } from "lucide-react";
import { api } from "../../lib/api";
import { cx, fmtDateTime, usd } from "../../lib/format";
import { Alert, Badge, Button, ErrorState, Field, Modal, PageLoader, useToast } from "../../components/ui";
import { can, FINANCE, PageHeader, Table, TableSkeleton, useAdmin } from "./AdminShell";

function Business() {
  const user = useAdmin();
  const admin = can(user, "ADMIN");
  const toast = useToast();
  const qc = useQueryClient();
  const { data, isLoading, error } = useQuery({ queryKey: ["admin-settings"], queryFn: () => api.get("/admin/settings/") });
  const [f, setF] = useState(null);
  const [files, setFiles] = useState({});
  useEffect(() => { if (data) setF(data); }, [data]);
  const save = useMutation({
    mutationFn: () => {
      const form = new FormData();
      ["business_name", "tagline", "business_email", "business_phone", "whatsapp_number", "business_address",
        "owner_notification_email", "invoice_footer", "invoice_terms", "payment_instructions", "tax_rate", "tax_label",
        "email_configuration_reference"].forEach((k) => form.append(k, f[k] ?? ""));
      Object.entries(files).forEach(([k, v]) => v && form.append(k, v));
      return api.uploadPatch("/admin/settings/", form);
    },
    onSuccess: (d) => { toast("Settings saved"); qc.setQueryData(["admin-settings"], d); qc.invalidateQueries({ queryKey: ["site"] }); setFiles({}); },
    onError: (e) => toast(e.message, "error"),
  });
  if (isLoading || !f) return <PageLoader />;
  if (error) return <ErrorState error={error} />;
  const inp = (k, label, props = {}) => <Field label={label} hint={props.hint}>{(a) => <input {...a} disabled={!admin} className="input" value={f[k] ?? ""} onChange={(e) => setF({ ...f, [k]: e.target.value })} {...props} />}</Field>;
  const area = (k, label, hint) => <Field label={label} hint={hint}>{(a) => <textarea {...a} disabled={!admin} rows={4} className="input" value={f[k] ?? ""} onChange={(e) => setF({ ...f, [k]: e.target.value })} />}</Field>;
  return (
    <div className="space-y-6">
      {!admin && <Alert tone="info">Only administrators can change business settings.</Alert>}
      <div className="card grid gap-4 p-5 sm:grid-cols-2">
        {inp("business_name", "Business name")}{inp("tagline", "Tagline")}
        {inp("business_email", "Public email", { type: "email" })}{inp("business_phone", "Public phone")}
        {inp("whatsapp_number", "WhatsApp number", { hint: "Digits with country code, no + or spaces — e.g. 255777123456" })}
        {inp("business_address", "Address")}
        {inp("owner_notification_email", "Owner notification email", { type: "email", hint: "New bookings, payments and enquiries are sent here." })}
        {inp("email_configuration_reference", "Email provider note", { hint: "For reference only (e.g. 'Brevo SMTP on Render'). Never enter passwords here." })}
      </div>
      <div className="card grid gap-4 p-5 sm:grid-cols-2">
        <Field label="Logo" hint="PNG/JPG/WebP, used on the website, invoices and receipts">{(a) => <input {...a} disabled={!admin} type="file" accept="image/png,image/jpeg,image/webp" className="input" onChange={(e) => setFiles({ ...files, logo: e.target.files?.[0] })} />}</Field>
        <Field label="Homepage hero photo" hint="Wide landscape photo, at least 2000px wide">{(a) => <input {...a} disabled={!admin} type="file" accept="image/png,image/jpeg,image/webp" className="input" onChange={(e) => setFiles({ ...files, hero_image: e.target.files?.[0] })} />}</Field>
        <div className="flex gap-4 sm:col-span-2">
          {data.logo_url && <img src={data.logo_url} alt="Current logo" className="h-14 rounded-lg border border-line bg-white p-2" />}
          {data.hero_image_url && <img src={data.hero_image_url} alt="Current hero" className="h-14 w-28 rounded-lg object-cover" />}
        </div>
      </div>
      <div className="card grid gap-4 p-5">
        {area("payment_instructions", "Manual payment instructions", "Bank and mobile-money details shown to guests who choose manual payment, and printed on invoices.")}
        {area("invoice_terms", "Invoice terms & notes")}
        {inp("invoice_footer", "Invoice footer")}
        <div className="grid gap-4 sm:grid-cols-2">
          {inp("tax_rate", "Tax rate (%)", { type: "number", step: "0.01", min: 0, max: 100, hint: "0 = no tax line on invoices" })}
          {inp("tax_label", "Tax label")}
        </div>
      </div>
      {admin && <Button loading={save.isPending} onClick={() => save.mutate()}>Save settings</Button>}
    </div>
  );
}

function Pricing() {
  const user = useAdmin();
  const edit = can(user, ...FINANCE);
  const toast = useToast();
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["admin-extras"], queryFn: () => api.get("/admin/extras/") });
  const [draft, setDraft] = useState(null);
  const save = useMutation({
    mutationFn: (x) => (x.id ? api.patch(`/admin/extras/${x.id}/`, x) : api.post("/admin/extras/", x)),
    onSuccess: () => { toast("Saved — new bookings use the updated price"); setDraft(null); qc.invalidateQueries({ queryKey: ["admin-extras"] }); qc.invalidateQueries({ queryKey: ["booking-options"] }); },
    onError: (e) => toast(e.message, "error"),
  });
  if (isLoading) return <TableSkeleton />;
  return (
    <>
      <Alert tone="info" className="mb-4">All fees are calculated by the server from this table. Changing a price affects new bookings only — existing bookings and invoices keep their original prices.</Alert>
      <div className="card overflow-hidden">
        <Table rows={data} onRow={edit ? (r) => setDraft({ ...r }) : undefined} columns={[
          { key: "n", label: "Service", render: (r) => <><span className="font-semibold">{r.name}</span>{r.is_system && <Badge tone="navy" className="ml-2">Core</Badge>}<span className="block text-xs text-muted">{r.description}</span></> },
          { key: "p", label: "Price", className: "text-right", render: (r) => <span className="font-semibold tabular-nums">{usd(r.price)}</span> },
          { key: "t", label: "Charged", render: (r) => ({ PER_BOOKING: r.code === "outside_zone_delivery" ? "Per leg" : "Per booking", PER_UNIT: "Per unit, per booking", PER_DAY: "Per day", PER_UNIT_PER_DAY: "Per unit, per day" })[r.pricing_type] },
          { key: "m", label: "Max qty", render: (r) => r.max_quantity },
          { key: "a", label: "Active", render: (r) => <Badge tone={r.is_active ? "green" : "slate"}>{r.is_active ? "Active" : "Off"}</Badge> },
        ]} />
      </div>
      {edit && <Button className="mt-4" variant="outline" icon={Plus} onClick={() => setDraft({ code: "", name: "", description: "", price: "", pricing_type: "PER_BOOKING", max_quantity: 1, is_active: true, display_order: 10 })}>Add service</Button>}
      <Modal open={!!draft} onClose={() => setDraft(null)} title={draft?.id ? `Edit ${draft.name}` : "New service"}
        footer={<><Button variant="ghost" onClick={() => setDraft(null)}>Cancel</Button><Button loading={save.isPending} onClick={() => save.mutate(draft)}>Save</Button></>}>
        {draft && <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Name">{(a) => <input {...a} className="input" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} />}</Field>
          <Field label="Code" hint="lowercase, e.g. gps_unit">{(a) => <input {...a} className="input" disabled={draft.is_system} value={draft.code} onChange={(e) => setDraft({ ...draft, code: e.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, "_") })} />}</Field>
          <Field label="Price (USD)">{(a) => <input {...a} type="number" step="0.01" min="0" className="input" value={draft.price} onChange={(e) => setDraft({ ...draft, price: e.target.value })} />}</Field>
          <Field label="Charged">{(a) => <select {...a} className="input" disabled={draft.is_system} value={draft.pricing_type} onChange={(e) => setDraft({ ...draft, pricing_type: e.target.value })}>
            <option value="PER_BOOKING">Per booking</option><option value="PER_UNIT">Per unit, per booking</option><option value="PER_DAY">Per day</option><option value="PER_UNIT_PER_DAY">Per unit, per day</option></select>}</Field>
          <Field label="Max quantity">{(a) => <input {...a} type="number" min="1" max="20" className="input" value={draft.max_quantity} onChange={(e) => setDraft({ ...draft, max_quantity: e.target.value })} />}</Field>
          <label className="flex items-center gap-2 self-end pb-3 text-sm"><input type="checkbox" className="size-4 accent-navy-900" checked={draft.is_active} onChange={(e) => setDraft({ ...draft, is_active: e.target.checked })} /> Active</label>
          <Field label="Description" className="sm:col-span-2">{(a) => <textarea {...a} rows={2} className="input" value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })} />}</Field>
        </div>}
      </Modal>
    </>
  );
}

function Testimonials() {
  const toast = useToast();
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["admin-testimonials"], queryFn: () => api.get("/admin/testimonials/") });
  const [draft, setDraft] = useState(null);
  const inv = () => qc.invalidateQueries({ queryKey: ["admin-testimonials"] });
  const save = useMutation({
    mutationFn: (x) => (x.id ? api.patch(`/admin/testimonials/${x.id}/`, x) : api.post("/admin/testimonials/", x)),
    onSuccess: () => { toast("Saved"); setDraft(null); inv(); }, onError: (e) => toast(e.message, "error"),
  });
  const remove = async (t) => { await api.del(`/admin/testimonials/${t.id}/`); inv(); };
  if (isLoading) return <TableSkeleton />;
  return (
    <>
      <Alert tone="warning" className="mb-4">Only publish genuine reviews from real guests, with their permission. The homepage section stays hidden until at least one review is published.</Alert>
      <div className="card overflow-hidden">
        <Table rows={data} onRow={(r) => setDraft({ ...r })} empty="No reviews yet." columns={[
          { key: "n", label: "Guest", render: (r) => <><span className="font-semibold">{r.customer_name}</span><span className="block text-xs text-muted">{r.country}</span></> },
          { key: "q", label: "Review", render: (r) => <span className="line-clamp-2 text-muted">{r.quote}</span> },
          { key: "r", label: "Rating", render: (r) => `${r.rating}/5` },
          { key: "p", label: "", render: (r) => <span className="flex items-center gap-2"><Badge tone={r.is_published ? "green" : "slate"}>{r.is_published ? "Published" : "Draft"}</Badge>
            <button onClick={(e) => { e.stopPropagation(); remove(r); }} className="grid size-8 place-items-center rounded-lg hover:bg-red-50" aria-label="Delete review"><Trash2 className="size-4 text-red-600" /></button></span> },
        ]} />
      </div>
      <Button className="mt-4" variant="outline" icon={Plus} onClick={() => setDraft({ customer_name: "", country: "", quote: "", rating: 5, is_published: false, display_order: 0 })}>Add review</Button>
      <Modal open={!!draft} onClose={() => setDraft(null)} title="Guest review"
        footer={<><Button variant="ghost" onClick={() => setDraft(null)}>Cancel</Button><Button loading={save.isPending} onClick={() => save.mutate(draft)}>Save</Button></>}>
        {draft && <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Guest name">{(a) => <input {...a} className="input" value={draft.customer_name} onChange={(e) => setDraft({ ...draft, customer_name: e.target.value })} />}</Field>
          <Field label="Country">{(a) => <input {...a} className="input" value={draft.country} onChange={(e) => setDraft({ ...draft, country: e.target.value })} />}</Field>
          <Field label="Review" className="sm:col-span-2">{(a) => <textarea {...a} rows={4} className="input" value={draft.quote} onChange={(e) => setDraft({ ...draft, quote: e.target.value })} />}</Field>
          <Field label="Rating">{(a) => <select {...a} className="input" value={draft.rating} onChange={(e) => setDraft({ ...draft, rating: Number(e.target.value) })}>{[5, 4, 3, 2, 1].map((n) => <option key={n}>{n}</option>)}</select>}</Field>
          <label className="flex items-center gap-2 self-end pb-3 text-sm"><input type="checkbox" className="size-4 accent-navy-900" checked={draft.is_published} onChange={(e) => setDraft({ ...draft, is_published: e.target.checked })} /> Publish on website</label>
        </div>}
      </Modal>
    </>
  );
}

function Messages() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["admin-messages"], queryFn: () => api.get("/admin/messages/") });
  const [open, setOpen] = useState(null);
  const toggle = async (m) => { await api.patch(`/admin/messages/${m.id}/`, { is_handled: !m.is_handled }); qc.invalidateQueries({ queryKey: ["admin-messages"] }); setOpen(null); };
  if (isLoading) return <TableSkeleton />;
  return (
    <div className="card overflow-hidden">
      <Table rows={data.results} onRow={setOpen} empty="No enquiries yet." columns={[
        { key: "d", label: "Received", render: (r) => fmtDateTime(r.created_at) },
        { key: "n", label: "From", render: (r) => <><span className="font-semibold">{r.name}</span><span className="block text-xs text-muted">{r.email}</span></> },
        { key: "s", label: "Subject", render: (r) => r.subject || <span className="text-muted line-clamp-1">{r.message}</span> },
        { key: "h", label: "", render: (r) => <Badge tone={r.is_handled ? "green" : "amber"}>{r.is_handled ? "Handled" : "New"}</Badge> },
      ]} />
      <Modal open={!!open} onClose={() => setOpen(null)} title={open?.subject || "Enquiry"}
        footer={open && <><Button variant="outline" href={`mailto:${open.email}?subject=Re: ${encodeURIComponent(open.subject || "Your enquiry")}`}>Reply by email</Button><Button onClick={() => toggle(open)}>{open.is_handled ? "Mark as new" : "Mark handled"}</Button></>}>
        {open && <><p className="text-sm text-muted">{open.name} · {open.email}{open.phone && ` · ${open.phone}`}</p><p className="mt-4 whitespace-pre-line">{open.message}</p></>}
      </Modal>
    </div>
  );
}

function EmailLog() {
  const toast = useToast();
  const qc = useQueryClient();
  const [status, setStatus] = useState("");
  const { data, isLoading } = useQuery({ queryKey: ["admin-notifications", status], queryFn: () => api.get("/admin/notifications/", { params: { delivery_status: status } }) });
  const resend = async (n) => { try { await api.post(`/admin/notifications/${n.id}/resend/`, {}); toast("Queued for delivery"); qc.invalidateQueries({ queryKey: ["admin-notifications"] }); } catch (e) { toast(e.message, "error"); } };
  return (
    <>
      <select className="input mb-4 w-56" aria-label="Delivery status" value={status} onChange={(e) => setStatus(e.target.value)}>
        <option value="">All emails</option><option value="FAILED">Failed — retrying</option><option value="ABANDONED">Failed — gave up</option><option value="QUEUED">Queued</option><option value="SENT">Sent</option>
      </select>
      <div className="card overflow-hidden">
        {isLoading ? <TableSkeleton /> : <Table rows={data.results} columns={[
          { key: "d", label: "Created", render: (r) => fmtDateTime(r.created_at) },
          { key: "t", label: "Email", render: (r) => <><span className="font-medium">{r.notification_type_display}</span><span className="block text-xs text-muted">{r.booking_reference}{r.invoice_number && ` · ${r.invoice_number}`}</span></> },
          { key: "r", label: "To", render: (r) => r.recipient },
          { key: "s", label: "Status", render: (r) => <><Badge status={r.delivery_status}>{r.delivery_status_display}</Badge>{r.error_message && <span className="mt-1 block max-w-xs truncate text-xs text-red-600" title={r.error_message}>{r.error_message}</span>}</> },
          { key: "a", label: "Attempts", render: (r) => r.attempts },
          { key: "x", label: "", render: (r) => <button onClick={() => resend(r)} className="grid size-8 place-items-center rounded-lg hover:bg-slate-100" aria-label="Resend"><Send className="size-4" /></button> },
        ]} />}
      </div>
    </>
  );
}

function AuditLog() {
  const { data, isLoading } = useQuery({ queryKey: ["admin-audit"], queryFn: () => api.get("/admin/audit-logs/") });
  if (isLoading) return <TableSkeleton />;
  return (
    <div className="card overflow-hidden">
      <Table rows={data.results} columns={[
        { key: "d", label: "When", render: (r) => fmtDateTime(r.created_at) },
        { key: "u", label: "Who", render: (r) => r.actor || <span className="text-muted">System / guest</span> },
        { key: "a", label: "Action", render: (r) => <code className="text-xs">{r.action}</code> },
        { key: "s", label: "Details", render: (r) => r.summary },
        { key: "i", label: "IP", render: (r) => <span className="text-xs text-muted">{r.ip_address}</span> },
      ]} />
    </div>
  );
}

export default function Settings() {
  const user = useAdmin();
  const tabs = [["business", "Business"], ["pricing", "Prices & services"], ["testimonials", "Reviews"], ["messages", "Enquiries"], ["email", "Email log"],
    ...(can(user, "ADMIN") ? [["audit", "Audit log"]] : [])];
  const [tab, setTab] = useState("business");
  return (
    <>
      <PageHeader title="Settings" />
      <div className="mb-6 flex flex-wrap gap-1 rounded-xl bg-slate-100 p-1 sm:w-fit" role="tablist">
        {tabs.map(([k, l]) => <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)} className={cx("rounded-lg px-4 py-2 text-sm font-semibold", tab === k ? "bg-white shadow-sm" : "text-muted")}>{l}</button>)}
      </div>
      {tab === "business" && <Business />}
      {tab === "pricing" && <Pricing />}
      {tab === "testimonials" && <Testimonials />}
      {tab === "messages" && <Messages />}
      {tab === "email" && <EmailLog />}
      {tab === "audit" && <AuditLog />}
    </>
  );
}
