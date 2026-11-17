import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ImagePlus, Plus, Search, Star, Trash2 } from "lucide-react";
import { api } from "../../lib/api";
import { usd } from "../../lib/format";
import { Alert, Badge, Button, ErrorState, Field, Modal, PageLoader, useToast } from "../../components/ui";
import { VehicleImage } from "../../components/VehicleCard";
import { can, FINANCE, PageHeader, Pager, Table, TableSkeleton, useAdmin } from "./AdminShell";

const CATEGORIES = [["ECONOMY", "Economy"], ["COMPACT", "Compact"], ["COMPACT_SUV", "Compact SUV"], ["SUV", "SUV"], ["4X4", "4x4 / Off-road"], ["MINIVAN", "Minivan"], ["LUXURY", "Luxury"]];

export function VehicleList() {
  const nav = useNavigate();
  const user = useAdmin();
  const [q, setQ] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [active, setActive] = useState("");
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["admin-vehicles", search, page, active], placeholderData: keepPreviousData,
    queryFn: () => api.get("/admin/vehicles/", { params: { search, page, is_active: active } }),
  });
  return (
    <>
      <PageHeader title="Vehicles" subtitle="Fleet, pricing, photos and availability."
        actions={can(user, ...FINANCE) && <Button to="/admin/vehicles/new" icon={Plus}>Add vehicle</Button>} />
      <div className="card mb-4 flex flex-col gap-3 p-4 sm:flex-row">
        <form className="relative flex-1" onSubmit={(e) => { e.preventDefault(); setSearch(q); setPage(1); }}>
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
          <input className="input pl-9" placeholder="Search name, brand, model…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search vehicles" />
        </form>
        <select className="input sm:w-48" aria-label="Active filter" value={active} onChange={(e) => { setActive(e.target.value); setPage(1); }}>
          <option value="">All vehicles</option><option value="true">Active only</option><option value="false">Inactive only</option>
        </select>
      </div>
      <div className="card overflow-hidden">
        {error ? <div className="p-4"><ErrorState error={error} onRetry={refetch} /></div> : isLoading ? <TableSkeleton /> : (
          <>
            <Table rows={data.results} onRow={(r) => nav(`/admin/vehicles/${r.id}`)} empty="No vehicles yet — add your first car."
              columns={[
                { key: "img", label: "", className: "w-20", render: (r) => <div className="h-12 w-16 overflow-hidden rounded-lg bg-slate-100"><VehicleImage vehicle={r} /></div> },
                { key: "name", label: "Vehicle", render: (r) => <><span className="flex items-center gap-1.5 font-semibold text-navy-900">{r.name}{r.is_featured && <Star className="size-3.5 fill-orange-500 text-orange-500" aria-label="Featured" />}</span><span className="text-xs text-muted">{r.brand} {r.model} · {r.category_display}</span></> },
                { key: "spec", label: "Specs", render: (r) => <span className="text-muted">{r.transmission_display} · {r.passenger_capacity} seats · {r.fuel_type_display}</span> },
                { key: "price", label: "Per day", className: "text-right", render: (r) => <span className="font-semibold tabular-nums">{usd(r.price_per_day)}</span> },
                { key: "bookings", label: "Bookings", className: "text-right", render: (r) => r.booking_count },
                { key: "status", label: "Status", render: (r) => <div className="flex flex-wrap gap-1"><Badge status={r.availability_status}>{r.availability_display}</Badge>{!r.is_active && <Badge tone="slate">Hidden</Badge>}</div> },
              ]} />
            <Pager data={data} page={page} setPage={setPage} />
          </>
        )}
      </div>
    </>
  );
}

const EMPTY = { name: "", brand: "", model: "", year: "", category: "SUV", description: "", price_per_day: "", transmission: "AUTOMATIC",
  fuel_type: "PETROL", passenger_capacity: 5, luggage_capacity: 2, doors: 4, availability_status: "AVAILABLE", is_featured: false,
  is_active: true, display_order: 0, features: [] };

export function VehicleForm() {
  const { id } = useParams();
  const isNew = id === "new";
  const nav = useNavigate();
  const qc = useQueryClient();
  const toast = useToast();
  const user = useAdmin();
  const editable = can(user, ...FINANCE);
  const q = useQuery({ queryKey: ["admin-vehicle", id], queryFn: () => api.get(`/admin/vehicles/${id}/`), enabled: !isNew });
  const [f, setF] = useState(EMPTY);
  const [featureText, setFeatureText] = useState("");
  const [err, setErr] = useState({});
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [uploading, setUploading] = useState(false);
  useEffect(() => { if (q.data) { setF({ ...EMPTY, ...q.data, year: q.data.year || "" }); setFeatureText(q.data.features.join("\n")); } }, [q.data]);

  const save = useMutation({
    mutationFn: () => {
      const body = { ...f, year: f.year || null, features: featureText.split("\n").map((s) => s.trim()).filter(Boolean) };
      delete body.images;
      return isNew ? api.post("/admin/vehicles/", body) : api.patch(`/admin/vehicles/${id}/`, body);
    },
    onSuccess: (v) => {
      toast(isNew ? "Vehicle added — now upload photos" : "Vehicle saved");
      qc.invalidateQueries({ queryKey: ["admin-vehicles"] }); qc.invalidateQueries({ queryKey: ["vehicles"] });
      if (isNew) nav(`/admin/vehicles/${v.id}`, { replace: true }); else qc.setQueryData(["admin-vehicle", id], v);
    },
    onError: (e) => { setErr(e.fieldErrors()); toast(e.message, "error"); },
  });
  const del = useMutation({
    mutationFn: () => api.del(`/admin/vehicles/${id}/`),
    onSuccess: (r) => { toast(r?.deactivated ? "Vehicle has bookings, so it was deactivated (hidden)" : "Vehicle deleted"); qc.invalidateQueries({ queryKey: ["admin-vehicles"] }); nav("/admin/vehicles"); },
    onError: (e) => toast(e.message, "error"),
  });
  const upload = async (files) => {
    if (!files?.length) return;
    setUploading(true);
    try {
      const form = new FormData();
      [...files].forEach((file) => form.append("images", file));
      await api.upload(`/admin/vehicles/${id}/images/`, form);
      toast(`${files.length} photo(s) uploaded`);
      q.refetch(); qc.invalidateQueries({ queryKey: ["vehicles"] });
    } catch (e) { toast(e.message, "error"); } finally { setUploading(false); }
  };
  const imageAction = async (img, action) => {
    try {
      if (action === "delete") await api.del(`/admin/vehicles/${id}/images/${img.id}/`);
      else await api.patch(`/admin/vehicles/${id}/images/${img.id}/`, { make_cover: true });
      q.refetch(); qc.invalidateQueries({ queryKey: ["vehicles"] });
    } catch (e) { toast(e.message, "error"); }
  };

  if (!isNew && q.isLoading) return <PageLoader />;
  if (q.error) return <ErrorState error={q.error} onRetry={q.refetch} />;
  const set = (k, v) => setF((x) => ({ ...x, [k]: v }));
  const input = (k, label, props = {}) => (
    <Field label={label} error={err[k]} required={props.required}>
      {(a) => <input {...a} {...props} disabled={!editable} className="input" value={f[k] ?? ""} onChange={(e) => set(k, e.target.value)} />}
    </Field>
  );

  return (
    <>
      <Link to="/admin/vehicles" className="inline-flex items-center gap-1.5 text-sm font-medium text-navy-700"><ArrowLeft className="size-4" /> All vehicles</Link>
      <PageHeader title={isNew ? "Add vehicle" : f.name} subtitle={!isNew && `/${q.data?.slug}`}
        actions={editable && <>
          {!isNew && <Button variant="outline" icon={Trash2} onClick={() => setConfirmDelete(true)}>Delete</Button>}
          <Button loading={save.isPending} onClick={() => save.mutate()}>{isNew ? "Create vehicle" : "Save changes"}</Button>
        </>} />
      <div className="grid gap-6 xl:grid-cols-[1.4fr_1fr]">
        <div className="card space-y-5 p-5">
          <div className="grid gap-4 sm:grid-cols-2">
            {input("name", "Display name", { required: true, placeholder: "e.g. Toyota RAV4 — Automatic" })}
            <Field label="Category" error={err.category}>{(a) => <select {...a} disabled={!editable} className="input" value={f.category} onChange={(e) => set("category", e.target.value)}>{CATEGORIES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>}</Field>
            {input("brand", "Brand", { required: true })}
            {input("model", "Model", { required: true })}
            {input("year", "Year", { type: "number", min: 1990, max: 2100 })}
            {input("price_per_day", "Price per day (USD)", { type: "number", step: "0.01", min: "1", required: true })}
            <Field label="Transmission">{(a) => <select {...a} disabled={!editable} className="input" value={f.transmission} onChange={(e) => set("transmission", e.target.value)}><option value="AUTOMATIC">Automatic</option><option value="MANUAL">Manual</option></select>}</Field>
            <Field label="Fuel">{(a) => <select {...a} disabled={!editable} className="input" value={f.fuel_type} onChange={(e) => set("fuel_type", e.target.value)}><option value="PETROL">Petrol</option><option value="DIESEL">Diesel</option><option value="HYBRID">Hybrid</option><option value="ELECTRIC">Electric</option></select>}</Field>
            {input("passenger_capacity", "Passengers", { type: "number", min: 1, max: 30 })}
            {input("luggage_capacity", "Luggage (bags)", { type: "number", min: 0, max: 20 })}
            {input("doors", "Doors", { type: "number", min: 2, max: 6 })}
            {input("display_order", "Display order", { type: "number", min: 0 })}
          </div>
          <Field label="Description" error={err.description}>{(a) => <textarea {...a} disabled={!editable} rows={5} className="input" value={f.description} onChange={(e) => set("description", e.target.value)} />}</Field>
          <Field label="Features" hint="One per line, e.g. Air conditioning, Bluetooth, 4WD">{(a) => <textarea {...a} disabled={!editable} rows={5} className="input" value={featureText} onChange={(e) => setFeatureText(e.target.value)} />}</Field>
        </div>
        <div className="space-y-6">
          <div className="card space-y-4 p-5">
            <h2 className="font-semibold">Availability</h2>
            <Field label="Status">{(a) => <select {...a} disabled={!editable} className="input" value={f.availability_status} onChange={(e) => set("availability_status", e.target.value)}><option value="AVAILABLE">Available</option><option value="MAINTENANCE">In maintenance</option><option value="UNAVAILABLE">Unavailable</option></select>}</Field>
            <label className="flex items-center gap-2.5 text-sm"><input type="checkbox" disabled={!editable} className="size-4 accent-navy-900" checked={f.is_active} onChange={(e) => set("is_active", e.target.checked)} /> Show on website</label>
            <label className="flex items-center gap-2.5 text-sm"><input type="checkbox" disabled={!editable} className="size-4 accent-navy-900" checked={f.is_featured} onChange={(e) => set("is_featured", e.target.checked)} /> Feature on homepage</label>
            <p className="text-xs text-muted">Price changes apply to new bookings only — existing bookings and invoices keep the price agreed at booking.</p>
          </div>
          {!isNew && (
            <div className="card p-5">
              <div className="flex items-center justify-between"><h2 className="font-semibold">Photos</h2>
                {editable && <label className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-line px-3 py-2 text-sm font-semibold hover:bg-navy-50">
                  <ImagePlus className="size-4" />{uploading ? "Uploading…" : "Upload"}
                  <input type="file" multiple accept="image/jpeg,image/png,image/webp" className="sr-only" onChange={(e) => upload(e.target.files)} disabled={uploading} />
                </label>}
              </div>
              {q.data?.images?.length ? (
                <ul className="mt-4 grid grid-cols-2 gap-3">
                  {q.data.images.map((img, i) => (
                    <li key={img.id} className="group relative overflow-hidden rounded-xl bg-slate-100">
                      <img src={img.url} alt={img.alt_text} className="aspect-[4/3] w-full object-cover" />
                      {i === 0 && <span className="absolute left-2 top-2"><Badge tone="orange" className="bg-white">Cover</Badge></span>}
                      {editable && <div className="absolute inset-x-0 bottom-0 flex justify-end gap-1 bg-gradient-to-t from-black/60 p-2">
                        {i > 0 && <button onClick={() => imageAction(img, "cover")} className="rounded-lg bg-white/90 px-2 py-1 text-xs font-semibold">Make cover</button>}
                        <button onClick={() => imageAction(img, "delete")} className="rounded-lg bg-white/90 p-1" aria-label="Delete photo"><Trash2 className="size-4 text-red-600" /></button>
                      </div>}
                    </li>
                  ))}
                </ul>
              ) : <Alert tone="warning" className="mt-4">No photos yet. Upload real photos of this car (landscape, at least 1600px wide) — they're shown on the fleet page.</Alert>}
            </div>
          )}
        </div>
      </div>
      <Modal open={confirmDelete} onClose={() => setConfirmDelete(false)} title="Delete vehicle?"
        footer={<><Button variant="ghost" onClick={() => setConfirmDelete(false)}>Cancel</Button><Button variant="danger" loading={del.isPending} onClick={() => del.mutate()}>Delete</Button></>}>
        <p className="text-sm text-muted">If this vehicle has any bookings it will be <strong>deactivated</strong> (hidden from the website) instead, so booking history and invoices stay intact.</p>
      </Modal>
    </>
  );
}
