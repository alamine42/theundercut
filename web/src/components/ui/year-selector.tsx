"use client";

import { useRouter } from "next/navigation";

interface YearSelectorProps {
  currentYear: number;
  basePath: string;
  availableYears: number[];
}

export function YearSelector({ currentYear, basePath, availableYears = [2024] }: YearSelectorProps) {
  const router = useRouter();

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const year = e.target.value;
    router.push(`${basePath}/${year}`);
  };

  return (
    <select
      value={currentYear}
      onChange={handleChange}
      className="h-10 px-3 border-2 border-ink bg-paper text-ink font-mono text-sm
                 focus:outline-none focus:ring-2 focus:ring-ink cursor-pointer
                 hover:bg-ink hover:text-paper transition-colors"
    >
      {availableYears.map((year) => (
        <option key={year} value={year}>
          {year}
        </option>
      ))}
    </select>
  );
}
