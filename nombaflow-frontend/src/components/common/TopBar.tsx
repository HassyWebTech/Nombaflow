import { Bell, Activity } from "lucide-react";

export default function TopBar() {
  const hour = new Date().getHours();

  const greeting =
    hour < 12
      ? "Good Morning"
      : hour < 18
      ? "Good Afternoon"
      : "Good Evening";

  return (
    <header className="mb-8 flex items-start justify-between">

      <div>

        <p className="text-sm font-medium text-slate-500">
          {greeting} 👋
        </p>

        <h1 className="mt-1 text-4xl font-extrabold tracking-tight text-[#081B33]">
          NombaFlow
        </h1>

        <p className="mt-2 text-sm text-slate-500">
          Recurring Billing Engine
        </p>

      </div>

      <div className="flex items-center gap-3">

        <div className="flex items-center gap-2 rounded-full bg-emerald-50 px-4 py-2">

          <Activity
            size={16}
            className="animate-pulse text-emerald-600"
          />

          <span className="text-xs font-bold tracking-wide text-emerald-700">
            HEALTHY • LIVE
          </span>

        </div>

        <button
          className="relative rounded-full bg-white p-3 shadow-md transition hover:scale-105 hover:shadow-xl"
          aria-label="Notifications"
        >

          <Bell
            size={20}
            className="text-[#081B33]"
          />

          <span className="absolute right-2 top-2 h-2.5 w-2.5 rounded-full bg-red-500"></span>

        </button>

      </div>

    </header>
  );
}