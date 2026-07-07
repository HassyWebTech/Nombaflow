import {
  CheckCircle2,
  Clock3,
  CreditCard,
  RefreshCcw,
} from "lucide-react";

import { motion } from "framer-motion";

const stages = [
  {
    title: "Created",
    icon: Clock3,
    color: "text-slate-500",
    bg: "bg-slate-100",
  },
  {
    title: "Scheduled",
    icon: RefreshCcw,
    color: "text-amber-500",
    bg: "bg-amber-100",
  },
  {
    title: "Charging",
    icon: CreditCard,
    color: "text-indigo-600",
    bg: "bg-indigo-100",
  },
  {
    title: "Paid",
    icon: CheckCircle2,
    color: "text-emerald-600",
    bg: "bg-emerald-100",
  },
];

export default function BillingEngine() {
  return (

    <section className="mt-8 rounded-[30px] border border-slate-200 bg-white p-6 shadow-sm">

      <div className="flex items-center justify-between">

        <div>

          <h2 className="text-2xl font-bold text-[#081B33]">
            Subscription Lifecycle
          </h2>

          <p className="mt-2 text-sm text-slate-500">
            Every recurring payment passes through this engine automatically.
          </p>

        </div>

        <div className="rounded-full bg-emerald-100 px-4 py-2 text-xs font-bold text-emerald-700 animate-pulse">
          LIVE
        </div>

      </div>

      <div className="mt-10 flex justify-between">

        {stages.map((stage, index) => {

          const Icon = stage.icon;

          return (

            <div
              key={stage.title}
              className="relative flex flex-1 flex-col items-center"
            >

              <motion.div
                animate={{
                  scale: [1, 1.08, 1],
                }}
                transition={{
                  repeat: Infinity,
                  duration: 2,
                  delay: index * .3,
                }}
                className={`z-10 flex h-16 w-16 items-center justify-center rounded-full ${stage.bg}`}
              >

                <Icon
                  size={28}
                  className={stage.color}
                />

              </motion.div>

              <span className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-600">
                {stage.title}
              </span>

              {index < stages.length - 1 && (

                <div className="absolute left-1/2 top-8 h-[3px] w-full overflow-hidden">

                  <motion.div
                    animate={{
                      x: ["-100%", "100%"],
                    }}
                    transition={{
                      repeat: Infinity,
                      duration: 2,
                      ease: "linear",
                    }}
                    className="h-full w-12 rounded-full bg-indigo-500"
                  />

                </div>

              )}

            </div>

          );

        })}

      </div>

      <div className="mt-10 rounded-3xl bg-slate-50 p-5">

        <div className="flex items-center justify-between">

          <span className="text-sm text-slate-500">
            Engine Status
          </span>

          <span className="font-bold text-emerald-600">
            418 Active Subscriptions
          </span>

        </div>

        <div className="mt-6 grid grid-cols-2 gap-4">

          <div className="rounded-2xl bg-white p-4">

            <p className="text-xs uppercase tracking-wide text-slate-500">
              Processed Today
            </p>

            <h3 className="mt-2 text-3xl font-bold text-[#081B33]">
              1,284
            </h3>

          </div>

          <div className="rounded-2xl bg-white p-4">

            <p className="text-xs uppercase tracking-wide text-slate-500">
              Webhooks Sent
            </p>

            <h3 className="mt-2 text-3xl font-bold text-[#081B33]">
              2,496
            </h3>

          </div>

        </div>

      </div>

    </section>

  );
}