// Import for type checking
import {
  checkPluginVersion,
  getDetailUrl,
  type InvenTreePluginContext,
  ModelType
} from '@inventreedb/ui';
import { t } from '@lingui/core/macro';
import {
  ActionIcon,
  Alert,
  Button,
  Divider,
  Group,
  Loader,
  Stack,
  Table,
  Text,
  Title
} from '@mantine/core';
import {
  IconCircleCheck,
  IconClipboardCheck,
  IconEye,
  IconRefresh
} from '@tabler/icons-react';
import { QueryClient, useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import { LocalizedComponent } from './locale';

const queryClient = new QueryClient();

const NEXT_ITEM_URL: string = '/plugin/rolling-stocktake/next/';

function RenderStockItem({
  context,
  item
}: {
  context: InvenTreePluginContext;
  item: any;
}) {
  const navigateToItem = () => {
    if (item?.pk) {
      context.navigate(getDetailUrl(ModelType.stockitem, item.pk));
    }
  };

  return (
    <Table.Tr>
      <Table.Td>
        {context.renderInstance({
          instance: item,
          model: ModelType.stockitem
        })}
      </Table.Td>
      <Table.Td>
        {item.location_detail ? (
          context.renderInstance({
            instance: item.location_detail,
            model: ModelType.stocklocation,
            extra: {
              show_location: false
            }
          })
        ) : (
          <Text size='sm' c='dimmed'>
            {t`No location`}
          </Text>
        )}
      </Table.Td>
      <Table.Td>
        {item.stocktake_date ? (
          <Text size='sm'>{item.stocktake_date}</Text>
        ) : (
          <Text c='red' size='sm'>
            {t`Never`}
          </Text>
        )}
      </Table.Td>
      <Table.Td>
        <Group gap='xs'>
          <ActionIcon
            color='blue'
            variant='light'
            onClick={navigateToItem}
            title={t`View Item`}
          >
            <IconEye size={16} />
          </ActionIcon>
        </Group>
      </Table.Td>
    </Table.Tr>
  );
}

function RenderStockItems({
  context,
  items
}: {
  context: InvenTreePluginContext;
  items: any[];
}) {
  const countStockForm: any = context?.forms.stockActions.countStock({
    items: items || [],
    model: ModelType.stockitem,
    refresh: () => {
      queryClient.invalidateQueries({ queryKey: ['next-item'] });
    }
  });

  if (!items || items.length === 0) {
    return (
      <Alert
        color='green'
        title={t`All up to date!`}
        icon={<IconCircleCheck />}
      >
        <Text size='sm'>{t`Nice work, you have counted enough items today.`}</Text>
      </Alert>
    );
  }

  return (
    <Stack gap='xs'>
      {countStockForm?.modal}
      <Table>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>{t`Stock Item`}</Table.Th>
            <Table.Th>{t`Location`}</Table.Th>
            <Table.Th>{t`Last Stocktake`}</Table.Th>
            <Table.Th>{t`Actions`}</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {items.map((item) => (
            <RenderStockItem key={item.pk} context={context} item={item} />
          ))}
        </Table.Tbody>
      </Table>
      <Divider />
      <Group grow>
        <Button
          color='green'
          variant='filled'
          leftSection={<IconClipboardCheck />}
          onClick={countStockForm.open}
        >
          {t`Count Stock`}
        </Button>
      </Group>
    </Stack>
  );
}

function RollingStocktakeDashboardItem({
  context
}: {
  context: InvenTreePluginContext;
}) {
  const itemQuery = useQuery(
    {
      enabled: true,
      queryKey: ['next-item'],
      queryFn: async () => {
        const response = await context.api?.get(NEXT_ITEM_URL);
        return response.data;
      }
    },
    queryClient
  );

  const stockItems = useMemo(() => {
    return itemQuery.data?.items ?? [];
  }, [itemQuery.data]);

  return (
    <Stack gap='xs'>
      <Group justify='space-between'>
        <Title c={context.theme.primaryColor} order={4}>
          {t`Rolling Stocktake`}
        </Title>
        <ActionIcon variant='transparent' onClick={() => itemQuery.refetch()}>
          <IconRefresh />
        </ActionIcon>
      </Group>
      <Divider />
      {(itemQuery.isLoading || itemQuery.isFetching) && <Loader size='sm' />}
      {!itemQuery.isLoading && !itemQuery.isFetching && itemQuery.isError && (
        <Alert color='red' title='Error'>
          <Text size='sm'>{t`Error loading stock information from server.`}</Text>
        </Alert>
      )}
      {!itemQuery.isLoading && itemQuery.isSuccess && (
        <RenderStockItems context={context} items={stockItems} />
      )}
    </Stack>
  );
}

// This is the function which is called by InvenTree to render the actual dashboard
//  component
export function renderRollingStocktakeDashboardItem(
  context: InvenTreePluginContext
) {
  checkPluginVersion(context);
  return (
    <LocalizedComponent locale={context.locale}>
      <RollingStocktakeDashboardItem context={context} />
    </LocalizedComponent>
  );
}
