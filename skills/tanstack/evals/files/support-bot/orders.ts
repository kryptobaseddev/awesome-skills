// src/server/orders.ts (existing, server-only)
export type OrderStatus = { orderId: string; status: 'processing' | 'shipped' | 'delivered' | 'cancelled'; eta?: string }
export async function lookupOrder(orderId: string, customerId: string): Promise<OrderStatus | null> {
  // queries the orders DB; customerId scopes the lookup to the signed-in customer
  return null
}
