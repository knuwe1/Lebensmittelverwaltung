import { Avatar } from '@mantine/core';
import { IconPackage } from '@tabler/icons-react';
import { productImageUrl } from '../api/hooks';
import type { Product } from '../api/types';

export function ProductAvatar({ product, size = 48 }: { product: Product; size?: number }) {
  return (
    <Avatar src={productImageUrl(product)} size={size} radius="md" alt="" color="green">
      <IconPackage size={size * 0.55} stroke={1.5} />
    </Avatar>
  );
}
