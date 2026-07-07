import {
  CreditCard,
  Wallet,
  RefreshCw,
  AlertTriangle,
} from "lucide-react";

import TopBar from "../components/common/TopBar";
import StatCard from "../components/common/StatCard";
import BillingEngine from "../components/dashboard/BillingEngine";

export default function Dashboard() {
  return (
    <main className="container-app">
      <TopBar />

      {/* ==========================
          HERO
      =========================== */}

      <section className="relative mb-8 overflow-hidden rounded-[32px] bg-[#081B33] p-7 text-white shadow-2xl">

        {/* Background Glow */}
        <div className="absolute -right-20 -top-20 h-56 w-56 rounded-full bg-indigo-500/30 blur-3xl" />
        <div className="absolute -bottom-20 left-0 h-48 w-48 rounded-full bg-cyan-400/20 blur-3xl" />

        <div className="relative">

          <span className="inline-flex items-center rounded-full bg-emerald-500/20 px-4 py-2 text-xs font-semibold tracking-wide text-emerald-300">
            ● BILLING ENGINE ONLINE
          </span>

          <h1 className="mt-6 text-4xl font-extrabold leading-tight md:text-5xl">
            Automate
            <br />
            Every Subscription.
          </h1>

          <p className="mt-5 max-w-md text-slate-300">
            NombaFlow automatically charges customers, retries failed payments,
            dispatches webhooks and keeps recurring revenue flowing.
          </p>

          {/* Hero Stats */}

          <div className="mt-8 grid grid-cols-3 gap-3">

            <div className="rounded-2xl bg-white/10 p-4 backdrop-blur">

              <p className="text-2xl font-bold">418</p>

              <p className="mt-1 text-[11px] uppercase tracking-widest text-slate-300">
                Active
              </p>

            </div>

            <div className="rounded-2xl bg-white/10 p-4 backdrop-blur">

              <p className="text-2xl font-bold">₦482K</p>

              <p className="mt-1 text-[11px] uppercase tracking-widest text-slate-300">
                Today
              </p>

            </div>

            <div className="rounded-2xl bg-white/10 p-4 backdrop-blur">

              <p className="text-2xl font-bold">99.4%</p>

              <p className="mt-1 text-[11px] uppercase tracking-widest text-slate-300">
                Success
              </p>

            </div>

          </div>

        </div>

      </section>

      {/* ==========================
          METRICS
      =========================== */}

      <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">

        <StatCard
          title="Revenue Today"
          value="₦482K"
          subtitle="+18% vs yesterday"
          icon={Wallet}
          color="#00C389"
        />

        <StatCard
          title="Subscriptions"
          value="418"
          subtitle="Currently active"
          icon={CreditCard}
        />

        <StatCard
          title="Retries"
          value="3"
          subtitle="Awaiting payment"
          icon={RefreshCw}
          color="#FFB020"
        />

        <StatCard
          title="Failed"
          value="1"
          subtitle="Needs attention"
          icon={AlertTriangle}
          color="#FF5A5F"
        />

      </section>

      {/* ==========================
          BILLING ENGINE
      =========================== */}

      <div className="mt-8">
        <BillingEngine />
      </div>

      {/* ==========================
          RECENT ACTIVITY
      =========================== */}

      <section className="mt-8 rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm">

        <div className="mb-6 flex items-center justify-between">

          <h2 className="text-xl font-bold text-[#081B33]">
            Recent Activity
          </h2>

          <button className="text-sm font-semibold text-indigo-600 transition hover:text-indigo-700">
            View all
          </button>

        </div>

        <div className="space-y-5">

          <Activity
            title="Netflix Premium"
            amount="₦4,500"
            status="Paid"
            color="bg-emerald-500"
          />

          <Activity
            title="Spotify"
            amount="₦2,200"
            status="Retrying"
            color="bg-amber-500"
          />

          <Activity
            title="ChatGPT Pro"
            amount="₦32,000"
            status="Paid"
            color="bg-emerald-500"
          />

        </div>

      </section>

      <div className="h-28" />

    </main>
  );
}

interface ActivityProps {
  title: string;
  amount: string;
  status: string;
  color: string;
}

function Activity({
  title,
  amount,
  status,
  color,
}: ActivityProps) {
  return (
    <div className="flex items-center justify-between rounded-2xl border border-slate-100 p-4 transition hover:shadow-md">

      <div className="flex items-center gap-4">

        <div className={`h-3 w-3 rounded-full ${color}`} />

        <div>

          <p className="font-semibold text-[#081B33]">
            {title}
          </p>

          <p className="text-sm text-slate-500">
            Subscription Payment
          </p>

        </div>

      </div>

      <div className="text-right">

        <p className="font-bold text-[#081B33]">
          {amount}
        </p>

        <p
          className={`text-xs font-semibold ${
            status === "Paid"
              ? "text-emerald-600"
              : "text-amber-600"
          }`}
        >
          {status}
        </p>

      </div>

    </div>
  );
}