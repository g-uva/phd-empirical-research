import {SimpleDataTable} from 'org_xprof/frontend/app/common/interfaces/data_table';
import {DefaultDataProvider} from 'org_xprof/frontend/app/components/chart/default_data_provider';

/** A device side analysis detail data provider. */
export class DeviceSideAnalysisDetailDataProvider extends DefaultDataProvider {
  columnIds: string[] = [];

  setColumnIds(columnIds: string[]) {
    this.columnIds = columnIds;
  }

  override parseData(
      data: SimpleDataTable|Array<Array<(string | number)>>|null) {
    if (!data) return;

    const dataTable = new google.visualization.DataTable(data);
    const dataView = new google.visualization.DataView(dataTable);

    dataView.setColumns(
        this.columnIds.map(columnId => dataTable.getColumnIndex(columnId)));

    this.dataTable = dataView.toDataTable();
  }
}
