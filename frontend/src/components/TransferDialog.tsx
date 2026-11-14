import { useState } from 'react';
import { Button, Modal, NumberInput, Stack, Text } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useBooking } from '../api/booking';
import type { StockItem } from '../api/types';
import { formatQuantity, unitShort } from '../lib/format';
import { LocationSelect } from './selects';
import { ExpiryText } from './ExpiryText';

/** Umlagerung einer Bestandsposition, ganz oder teilweise (FR-MOV-001/002). */
export function TransferDialog({ item, onClose }: { item: StockItem | null; onClose: () => void }) {
  return (
    <Modal opened={item !== null} onClose={onClose} title="Umlagern">
      {item && <TransferForm key={item.id} item={item} onClose={onClose} />}
    </Modal>
  );
}

function TransferForm({ item, onClose }: { item: StockItem; onClose: () => void }) {
  const [quantity, setQuantity] = useState<string | number>(item.quantity);
  const [target, setTarget] = useState<string | null>(null);
  const booking = useBooking('/stock/transfers', (r) => {
    notifications.show({
      color: 'green',
      message: `${formatQuantity(r.quantity, item.base_unit)} ${item.product_name} umgelagert.`,
    });
    onClose();
  });
  const qty = Number(quantity);
  return (
    <Stack>
      <div>
        <Text fw={600}>{item.product_name}</Text>
        <Text size="sm" c="dimmed">
          {item.location_path} · {formatQuantity(item.quantity, item.base_unit)} · <ExpiryText item={item} />
        </Text>
      </div>
      <NumberInput
        label={`Menge (${unitShort(item.base_unit)})`}
        min={0}
        max={item.quantity}
        decimalScale={3}
        decimalSeparator=","
        thousandSeparator="."
        inputMode="decimal"
        value={quantity}
        onChange={setQuantity}
      />
      <LocationSelect label="Ziellagerplatz" value={target} onChange={setTarget} excludeId={item.location_id} required />
      <Button
        size="lg"
        disabled={!target || !(qty > 0) || qty > item.quantity}
        loading={booking.isPending}
        onClick={() =>
          booking.mutate({
            stock_item_id: item.id,
            quantity: qty,
            target_location_id: target,
            expected_version: item.version,
          })
        }
      >
        Umlagern
      </Button>
    </Stack>
  );
}
