"""
用于轨迹数据获取分析

Author: CheneyZhao.wust.edu
        cheneyzhao@126.com
"""
import csv
from datastore import AterialDataCollection
from typing import Any, Generator
import numpy as np


class GetVisTrajectoryData(AterialDataCollection):
    def __init__(self, LoadNet_name: str, LoadLayout_name: str,
                 link_num_inbound: list, link_num_outbound: list, /,
                 period: int = 3600, seed: list = None, step: int = 10, Warm_time: int = 600):
        """
        GetVisTrajectoryData用于获取Vis-sim在仿真过程中车辆在干线方向的轨迹数据
        :param period: 单次仿真周期时长，默认3600s -> int
        :param seed: 仿真随机种子
        :param step: 仿真随机种子迭代步长 -> int
        ------------------------------------------------------------------------------------------
        '若输入为区间，上下边界[Lower boundary[int], Upper boundary[int]], 需要设定单次迭代步长step -> int'
        '若输入为列表，seed = [arg1[int], arg2[int], ...], 按遍历列表内部元素进行随机种子设定              '
        '默认为区间：[10, 200], step = 10                                                            '
        -------------------------------------------------------------------------------------------
        :param Warm_time: 仿真预热时间，默认600s -> int
        :param LoadNet_name: Vis-sim inp文件位置 -> str
        :param LoadLayout_name: Vis-sim in0文件位置 -> str
        :param link_num_inbound: inbound干线路段编号 -> list[int]
        :param link_num_outbound: outbound干线路段编号 -> list[int]
        """
        super().__init__(LoadNet_name, LoadLayout_name)
        if seed is None:
            seed = [10, 200]
        self.period = period
        self.seed = seed
        self.step = step
        self.Warm_time = Warm_time
        self.link_num_inbound_ = link_num_inbound
        self.link_num_outbound_ = link_num_outbound

    def _set_randomseed(self, seed: int):
        self.Sim.RandomSeed = seed

    @staticmethod
    def _print_progress(seed: int):
        print(f'Current simulation, seed = {seed}, please be patient...')

    def _running_warm(self):
        for i in range(self.Warm_time * 5):
            self.Sim.RunSingleStep()

    @staticmethod
    def _creat_ids():
        return ()

    def _get_vehicle_drive_data(self) -> tuple:
        ids = self.vnet.Vehicles.IDs
        link = self.vnet.Vehicles.GetMultiAttValues(ids, 'LINK')
        speed = self.vnet.Vehicles.GetMultiAttValues(ids, 'SPEED')
        time_ = self.Sim.AttValue('ELAPSEDTIME')
        dis = self.vnet.Vehicles.GetMultiAttValues(ids, 'TOTALDISTANCE')

        return ids, link, speed, time_, dis

    @staticmethod
    def _creat_cantiner_dict(ids: tuple) -> dict[Any, list[Any]]:
        """
        生成车辆数据容器
        :param ids: 当前路网内车辆所有ID
        :return: dict{id:[drive data]}
        """
        return dict([(k, []) for k in ids])

    def _vehicle_drive_data_set(self, ids: tuple) -> Generator[dict[Any, list[Any]], Any, None]:
        """
        返回数据集合
        :param ids: 当前路网内车辆所有ID
        :return: Lik, Time, Dis, Spd容器用于储存不同ID对应link, speed, time, distance
        """
        return (self._creat_cantiner_dict(ids) for _ in range(4))

    @staticmethod
    def _judge_new_cars(ids: tuple, old_ids: tuple) -> list:
        # old_ids 与 ids差集
        return list(set(ids).difference(set(old_ids)))

    @staticmethod
    def _setdefault_drive_data(index_: int, Lik: dict, Time: dict, Dis: dict, Spd: dict, ids: tuple, link: tuple,
                               speed: tuple, time_: tuple, dis: tuple) -> tuple[dict, dict, dict, dict]:
        # Lik.setdefault(index_, []).append(link[ids.index(index_)])
        # Time.setdefault(index_, []).append(time)
        # Dis.setdefault(index_, []).append(dis[ids.index(index_)])
        # Spd.setdefault(index_, []).append(speed[ids.index(index_)])
        # return Lik, Time, Dis, Spd
        dicts = (Lik, Dis, Spd)
        values = (link, dis, speed)
        for d, v in zip(dicts, values):
            # 使用 setdefault 方法设置默认值，并追加新值
            # ids.index(index) 用于获取 index 在 ids 列表中的索引位置
            d.setdefault(index_, []).append(v[ids.index(index_)])
        Time.setdefault(index_, []).append(time_)
        return Lik, Time, Dis, Spd

    @staticmethod
    def _update_drive_data(index_: int, Lik: dict, Time: dict, Dis: dict, Spd: dict) -> tuple:
        # Lik.update({index_: []})
        # Time.update({index_: []})
        # Dis.update({index_: []})
        # Spd.update({index_: []})
        dicts = [Lik, Time, Dis, Spd]
        for d in dicts:
            d.update({index_: []})
        return Lik, Time, Dis, Spd

    @staticmethod
    def _creat_cantiner_list() -> list[list]:
        return [[] for _ in range(6)]

    def _sift_out_arterial_data(self, Lik: dict, Time: dict, Dis: dict, Spd: dict) -> tuple:
        """
        筛除非干线轨迹数据
        :param Lik: link集合
        :param Time: 路网车辆时间戳
        :param Dis: 路网车辆位置戳
        :param Spd: 路网车辆速度戳
        :return: 干线轨迹数据
                time_：时间戳集合 -> list[list[single_vehicle_trajectories_data[float]], ...]
                distance_：位置戳集合 -> list[list[single_vehicle_trajectories_data[float]], ...]
                speed_：速度戳集合 -> list[list[single_vehicle_trajectories_data[float]], ...]
        """
        # 生成数据存储容器
        time_inbound, time_outbound, speed_inbound, speed_outbound, \
            distance_inbound, distance_outbound = self._creat_cantiner_list()

        def extract_values(ID_, dict_):
            return list(np.ravel([v for k, v in dict_.items() if k == ID_]))

        for ID, car_link in Lik.items():
            lk = list(set(car_link))
            if self.link_num_outbound_[0] in lk and self.link_num_outbound_[-1] in lk:
                speed_outbound.append(extract_values(ID, Spd))
                distance_outbound.append(extract_values(ID, Dis))
                time_outbound.append(extract_values(ID, Time))
            elif self.link_num_inbound_[0] in lk and self.link_num_inbound_[-1] in lk:
                speed_inbound.append(extract_values(ID, Spd))
                distance_inbound.append(extract_values(ID, Dis))
                time_inbound.append(extract_values(ID, Time))

        return time_inbound, distance_inbound, speed_inbound, time_outbound, distance_outbound, speed_outbound

    def _single_vis_trajectorydata(self):

        # 获取数据
        ids: tuple = self._creat_ids()
        # 生成虚拟行驶数据容器
        Lik, Time, Dis, Spd = self._vehicle_drive_data_set((1, 2, 3, 4))
        # 仿真读取数据
        for i in range((self.period - self.Warm_time) * 5):
            old_ids = ids
            self.Sim.RunSingleStep()
            # 获取路网车辆驾驶数据集
            ids, link, speed, time_, dis = self._get_vehicle_drive_data()

            if i == 0:
                # 生成行驶数据容器
                Lik, Time, Dis, Spd = self._vehicle_drive_data_set(ids)
                for j in ids:
                    # 初始化路网车辆行驶数据
                    Lik, Time, Dis, Spd = self._setdefault_drive_data(j, Lik, Time, Dis, Spd,
                                                                      ids, link, speed, time_,
                                                                      dis)
            else:
                # 在后续更新进入路网车辆ID产生新的容器，未驶出路网车辆使用已有设定容器
                new_cars: list = self._judge_new_cars(ids, old_ids)
                for k in new_cars:
                    if k not in Lik.keys():
                        Lik, Time, Dis, Spd = self._update_drive_data(k, Lik, Time, Dis, Spd)

                for j in ids:
                    Lik, Time, Dis, Spd = self._setdefault_drive_data(j, Lik, Time, Dis, Spd,
                                                                      ids, link, speed, time_,
                                                                      dis)
        # 对路网轨迹数据进行处理，筛出干线轨迹数据
        time_inbound, distance_inbound, speed_inbound, \
            time_outbound, distance_outbound, speed_outbound = self._sift_out_arterial_data(Lik, Time, Dis, Spd)

        return time_inbound, distance_inbound, speed_inbound, time_outbound, distance_outbound, speed_outbound

    def _update_trajectorydata(self, seed: int, inbound_tradata: dict, outbound_tradata: dict) -> tuple:

        self._print_progress(seed)  # 当前进程
        self._set_randomseed(seed)  # 设置当前仿真随机种子
        self._running_warm()  # 预热
        # 单次仿真数据
        time_inbound, distance_inbound, speed_inbound, \
            time_outbound, distance_outbound, speed_outbound = self._single_vis_trajectorydata()
        # {seed, trajectorydata}
        inbound_tradata.update({str(seed): (time_inbound, distance_inbound, speed_inbound)})
        outbound_tradata.update({str(seed): (time_outbound, distance_outbound, speed_outbound)})

        return inbound_tradata, outbound_tradata

    # 从Vis-sim中获取轨迹数据
    def get_vis_trajectorydata(self) -> tuple[dict[str, tuple[Any, Any, Any]], dict[str, tuple[Any, Any, Any]]]:
        """
        获取轨迹数据
        :return: inbound轨迹数据 -> dict{seed, trajectorydata}
                 outbound轨迹数据 -> dict{seed, trajectorydata}
        """
        inbound_traydata, outbound_tradata = {}, {}  # 数据存储器
        if len(self.seed) > 2:
            for s in self.seed:
                inbound_traydata, outbound_tradata = self._update_trajectorydata(s, inbound_traydata, outbound_tradata)
                self.Sim.Stop()  # 终止仿真
        else:
            for s in range(self.seed[0], self.seed[1] + 1, self.step):
                inbound_traydata, outbound_tradata = self._update_trajectorydata(s, inbound_traydata, outbound_tradata)
                self.Sim.Stop()  # 终止仿真

        return inbound_traydata, outbound_tradata


class ExternalTrajectoryData:
    def __init__(self, filename: str, direction: str):
        """
        外部导入轨迹数据输出评价数据及轨迹pkl文件，用于绘图
        :param filename: 轨迹文件名，csv文件
        :param direction: 轨迹方向，标识符 -> inbound or outbound
        """
        self.filename = filename
        self.direction = direction

    @staticmethod
    def _creat_cantiner():
        return [[] for _ in range(3)]

    def _read_csv(self):
        # 打开CSV文件
        try:
            # 打开CSV文件
            with open(self.filename, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                # 读取第一行
                first_row = next(reader)
                # 判断元素个数是否为3的倍数
                if len(first_row) % 3 != 0:
                    print("Error Data")
                else:
                    # 创建与列数相同数量的空列表
                    column_count = len(first_row)
                    column_lists = [[] for _ in range(column_count)]
                    # 读取剩余的所有行
                    for row in reader:
                        for index, value in enumerate(row):
                            column_lists[index].append(float(value))
                    # 将列列表添加到总列表中
                    all_data = column_lists
                    return all_data
        except FileNotFoundError:
            print(f"can't find document {self.filename}, Please check the file path.")
        except Exception as e:
            print(f"An error occurred while reading the file: {e}")

    def sys_trajectory(self):
        all_data = self._read_csv()
        time, distance, speed = self._creat_cantiner()
        for i in range(0, len(all_data), 3):
            time_ID, distance_ID, speed_ID = all_data[i:i + 3]
            time.append(time_ID)
            distance.append(distance_ID)
            speed.append(speed_ID)
        bound_data = {self.direction: (time, distance, speed)}
        return bound_data


if __name__ == "__main__":
    print('get trajectory from VIS-SIM')
