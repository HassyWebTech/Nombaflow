import { TrendingUp } from "lucide-react";
import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon: LucideIcon;
  color?: string;
}

export default function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  color = "#5B5CEB",
}: StatCardProps) {

  return (

    <div className="group rounded-[28px] border border-slate-200 bg-white p-5 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-2xl">

      <div className="flex items-center justify-between">

        <div
          className="flex h-14 w-14 items-center justify-center rounded-2xl"
          style={{
            backgroundColor: `${color}15`,
          }}
        >
          <Icon
            size={24}
            color={color}
          />
        </div>

        <TrendingUp
          size={18}
          className="text-emerald-500"
        />

      </div>

      <p className="mt-5 text-sm font-medium text-slate-500">
        {title}
      </p>

      <h2 className="mt-2 text-4xl font-extrabold tracking-tight text-[#081B33]">
        {value}
      </h2>

      {subtitle && (

        <p className="mt-2 text-sm text-slate-400">
          {subtitle}
        </p>

      )}

    </div>

  );
}