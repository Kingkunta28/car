import { lazy, StrictMode, Suspense } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "./index.css";
import "./i18n";
import PublicLayout from "./components/Layout";
import { PageLoader, ToastProvider } from "./components/ui";
import Home from "./pages/public/Home";

// Route-level code splitting: the admin dashboard never loads for guests.
const Fleet = lazy(() => import("./pages/public/Fleet"));
const VehicleDetail = lazy(() => import("./pages/public/VehicleDetail"));
const Booking = lazy(() => import("./pages/public/Booking"));
const Confirmation = lazy(() => import("./pages/public/Confirmation"));
const ManageBooking = lazy(() => import("./pages/public/ManageBooking"));
const PaymentReturn = lazy(() => import("./pages/public/PaymentReturn"));
const info = () => import("./pages/public/InfoPages");
const About = lazy(() => info().then((m) => ({ default: m.About })));
const Contact = lazy(() => info().then((m) => ({ default: m.Contact })));
const BeforeYouRent = lazy(() => info().then((m) => ({ default: m.BeforeYouRent })));
const Privacy = lazy(() => info().then((m) => ({ default: m.Privacy })));
const Terms = lazy(() => info().then((m) => ({ default: m.Terms })));
const NotFound = lazy(() => info().then((m) => ({ default: m.NotFound })));

const shell = () => import("./pages/admin/AdminShell");
const AdminShell = lazy(() => shell().then((m) => ({ default: m.AdminShell })));
const AdminLogin = lazy(() => shell().then((m) => ({ default: m.AdminLogin })));
const Overview = lazy(() => import("./pages/admin/Overview"));
const Bookings = lazy(() => import("./pages/admin/Bookings"));
const BookingDetail = lazy(() => import("./pages/admin/BookingDetail"));
const veh = () => import("./pages/admin/Vehicles");
const VehicleList = lazy(() => veh().then((m) => ({ default: m.VehicleList })));
const VehicleForm = lazy(() => veh().then((m) => ({ default: m.VehicleForm })));
const rec = () => import("./pages/admin/Records");
const Customers = lazy(() => rec().then((m) => ({ default: m.Customers })));
const CustomerDetail = lazy(() => rec().then((m) => ({ default: m.CustomerDetail })));
const Invoices = lazy(() => rec().then((m) => ({ default: m.Invoices })));
const Payments = lazy(() => rec().then((m) => ({ default: m.Payments })));
const Reports = lazy(() => import("./pages/admin/Reports"));
const Settings = lazy(() => import("./pages/admin/Settings"));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: (n, err) => n < 2 && !(err?.status >= 400 && err?.status < 500), refetchOnWindowFocus: false },
  },
});

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <BrowserRouter>
          <Suspense fallback={<PageLoader />}>
            <Routes>
              <Route element={<PublicLayout />}>
                <Route index element={<Home />} />
                <Route path="fleet" element={<Fleet />} />
                <Route path="fleet/:slug" element={<VehicleDetail />} />
                <Route path="book" element={<Booking />} />
                <Route path="booking/confirmation/:bookingReference" element={<Confirmation />} />
                <Route path="booking/confirmation" element={<Confirmation />} />
                <Route path="booking/manage" element={<ManageBooking />} />
                <Route path="invoice" element={<ManageBooking />} />
                <Route path="payment/return" element={<PaymentReturn />} />
                <Route path="about" element={<About />} />
                <Route path="contact" element={<Contact />} />
                <Route path="before-you-rent" element={<BeforeYouRent />} />
                <Route path="privacy" element={<Privacy />} />
                <Route path="terms" element={<Terms />} />
                <Route path="*" element={<NotFound />} />
              </Route>
              <Route path="admin/login" element={<AdminLogin />} />
              <Route path="admin" element={<AdminShell />}>
                <Route index element={<Overview />} />
                <Route path="bookings" element={<Bookings />} />
                <Route path="bookings/:id" element={<BookingDetail />} />
                <Route path="vehicles" element={<VehicleList />} />
                <Route path="vehicles/:id" element={<VehicleForm />} />
                <Route path="customers" element={<Customers />} />
                <Route path="customers/:id" element={<CustomerDetail />} />
                <Route path="invoices" element={<Invoices />} />
                <Route path="payments" element={<Payments />} />
                <Route path="reports" element={<Reports />} />
                <Route path="settings" element={<Settings />} />
              </Route>
            </Routes>
          </Suspense>
        </BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>
  </StrictMode>,
);
