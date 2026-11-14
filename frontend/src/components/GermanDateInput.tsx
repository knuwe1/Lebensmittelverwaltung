import { DateInput } from '@mantine/dates';
import type { DateInputProps } from '@mantine/dates';
import { parseGermanDate } from '../lib/format';

/** Datumseingabe, die getippte deutsche Daten versteht (z. B. "20.11.27" oder "201127"). */
export function GermanDateInput(props: DateInputProps) {
  return (
    <DateInput
      valueFormat="DD.MM.YYYY"
      placeholder="TT.MM.JJJJ"
      dateParser={(value) => parseGermanDate(value)}
      inputMode="numeric"
      clearable
      {...props}
    />
  );
}
