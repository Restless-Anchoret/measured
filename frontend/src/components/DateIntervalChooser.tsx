import { useState, useEffect } from 'react';
import {
  startOfWeek,
  endOfWeek,
  startOfMonth,
  endOfMonth,
  startOfYear,
  endOfYear,
  addWeeks,
  addMonths,
  addYears,
  addDays,
  format,
} from 'date-fns';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { IntervalKind, AggregationBy } from '@/types';
import type { DateRange } from '@/types';

interface DateIntervalChooserProps {
  onChange: (dateRange: DateRange) => void;
}

type SelectionType = 'weeks-by-day' | 'months-by-day' | 'years-by-weeks' | 'years-by-months';

const SELECTION_OPTIONS: Array<{ value: SelectionType; label: string }> = [
  { value: 'weeks-by-day', label: 'Weeks by day' },
  { value: 'months-by-day', label: 'Months by day' },
  { value: 'years-by-weeks', label: 'Years by weeks' },
  { value: 'years-by-months', label: 'Years by months' },
];

const weekOptions = { weekStartsOn: 1 as const }; // Monday

export default function DateIntervalChooser({ onChange }: DateIntervalChooserProps) {
  const [selectionType, setSelectionType] = useState<SelectionType>('weeks-by-day');
  const [currentDate, setCurrentDate] = useState<Date>(new Date());

  // Calculate interval kind and aggregation based on selection type
  const getIntervalConfig = (type: SelectionType) => {
    switch (type) {
      case 'weeks-by-day':
        return { intervalKind: IntervalKind.WEEK, aggregationBy: AggregationBy.DAY };
      case 'months-by-day':
        return { intervalKind: IntervalKind.MONTH, aggregationBy: AggregationBy.DAY };
      case 'years-by-weeks':
        return { intervalKind: IntervalKind.YEAR, aggregationBy: AggregationBy.WEEK };
      case 'years-by-months':
        return { intervalKind: IntervalKind.YEAR, aggregationBy: AggregationBy.MONTH };
    }
  };

  // Calculate fromDate and toDate based on current date and selection type
  const getDateRange = (date: Date, type: SelectionType) => {
    const config = getIntervalConfig(type);
    let fromDate: Date;
    let toDate: Date;

    switch (config.intervalKind) {
      case IntervalKind.WEEK:
        fromDate = startOfWeek(date, weekOptions);
        toDate = addDays(endOfWeek(date, weekOptions), 1);
        break;
      case IntervalKind.MONTH:
        fromDate = startOfMonth(date);
        toDate = addDays(endOfMonth(date), 1);
        break;
      case IntervalKind.YEAR:
        fromDate = startOfYear(date);
        toDate = addDays(endOfYear(date), 1);
        break;
    }

    return { fromDate, toDate, ...config };
  };

  // Format the display text based on selection type
  const getDisplayText = (date: Date, type: SelectionType) => {
    const config = getIntervalConfig(type);

    switch (config.intervalKind) {
      case IntervalKind.WEEK: {
        const start = startOfWeek(date, weekOptions);
        const end = endOfWeek(date, weekOptions);
        return `${format(start, 'MMM d')} - ${format(end, 'MMM d, yyyy')}`;
      }
      case IntervalKind.MONTH:
        return format(date, 'MMMM yyyy');
      case IntervalKind.YEAR:
        return format(date, 'yyyy');
    }
  };

  // Navigate to previous or next interval
  const handleNavigate = (direction: -1 | 1) => {
    const config = getIntervalConfig(selectionType);
    let newDate: Date;

    switch (config.intervalKind) {
      case IntervalKind.WEEK:
        newDate = addWeeks(currentDate, direction);
        break;
      case IntervalKind.MONTH:
        newDate = addMonths(currentDate, direction);
        break;
      case IntervalKind.YEAR:
        newDate = addYears(currentDate, direction);
        break;
    }

    const range = getDateRange(newDate, selectionType);
    onChange(range);
    setCurrentDate(newDate);
  };

  // Handle selection type change
  const handleSelectionTypeChange = (newType: SelectionType) => {
    const oldConfig = getIntervalConfig(selectionType);
    const newConfig = getIntervalConfig(newType);

    // If both are years, preserve the selected year
    if (
      oldConfig.intervalKind === IntervalKind.YEAR &&
      newConfig.intervalKind === IntervalKind.YEAR
    ) {
      // Keep the current date (year is preserved)
      const range = getDateRange(currentDate, newType);
      onChange(range);
      setSelectionType(newType);
    } else {
      // Otherwise, jump to interval containing today
      const today = new Date();
      const range = getDateRange(today, newType);
      onChange(range);
      setCurrentDate(today);
      setSelectionType(newType);
    }
  };

  // Call onChange on mount with initial values
  useEffect(() => {
    const range = getDateRange(currentDate, selectionType);
    onChange(range);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex flex-col md:flex-row items-start md:items-center gap-4">
      {/* Interval Navigator */}
      <div className="flex items-center gap-2 border rounded-md">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => handleNavigate(-1)}
          className="h-10 w-10"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <div className="min-w-[200px] text-center text-sm font-medium">
          {getDisplayText(currentDate, selectionType)}
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => handleNavigate(1)}
          className="h-10 w-10"
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      {/* Selection Type Dropdown */}
      <Select value={selectionType} onValueChange={handleSelectionTypeChange}>
        <SelectTrigger className="w-[180px]">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {SELECTION_OPTIONS.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

