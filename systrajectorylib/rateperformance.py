"""
评级方法，用于基于评价模型对干线性能进行评级

Author: CheneyZhao.wust.edu
           cheneyzhao@126.com
"""
import bisect
import math
import numpy as np
from typing import Union, Any, Optional
import csv
import os


# output Percent on Green
def output_POG(single_purdue_data: dict, purdue_BOG_EOG: dict) -> float:
    """
    用于输出车辆在绿灯期间到达率, 忽略第一个交叉口产生的 out of green
    :param single_purdue_data: 单向普渡数据 -> dict{seed: dict{s_num: tuple[time, arrival time]}}
    :param purdue_BOG_EOG: begin on green and end on green， transplotlib output this parameter
                            -> dict{s_num: tuple[BOG, EOG]} or dict{s_num: list[((BOG, EOG), base_cycle, cycle), ...]}
    :return: percent_on_green -> float
    """
    percent_on_green_set = []  # 存储所有层级下的percent_on_green

    def del_frist_interinfo(value):  # 删除第一个交叉口信息
        first_key = next(iter(value))
        del value[first_key]
        return value

    def find_index_bound(data_, bound):
        left, right = bound
        start_ = bisect.bisect_left(data_, left)
        end_ = bisect.bisect_right(data_, right) - 1
        # 始终返回长度为2的列表，用 -1 标记无效区间
        return [start_, end_] if start_ <= end_ else [None, None]

    purdue_BOG_EOG = del_frist_interinfo(purdue_BOG_EOG)

    for seed, data in single_purdue_data.items():
        data = del_frist_interinfo(data)

        for s_num, seed_data in data.items():
            if type(purdue_BOG_EOG[s_num]) is list:
                # bound_BOG_EOG: list -> [(bog_eog, base_cycle, cycle), ...]
                for value_sum_seed in seed_data:  # value_sum_seed -> tuple[tuple[list[net_time], list[arrive_time]]]
                    # 获取车辆在那个周期区间内 共有len([(当前周期bog_eog:tuple, 当前周期叠加时间, 当前周期时长), ...])个周期
                    low_bound = 0
                    for n in range(len(purdue_BOG_EOG[s_num])):
                        # value_sum_seed[0] -> list[net_time]
                        # 找到时间片段
                        [start, end] = find_index_bound(value_sum_seed[0], [low_bound, purdue_BOG_EOG[s_num][n][1]])
                        low_bound += purdue_BOG_EOG[s_num][n][2]

                        if start != end:
                            # value_sum_seed[1] -> list[arrive_time]
                            count = sum(1 for arrival_time in value_sum_seed[1][start:end] if
                                        purdue_BOG_EOG[s_num][n][0][0] <= arrival_time <= purdue_BOG_EOG[s_num][n][0][
                                            1])
                            percent_on_green_set.append(count / len(value_sum_seed[1][start:end]))

            else:
                count = sum(1 for data_ in seed_data for arrival_time in data_[1] if
                            purdue_BOG_EOG[s_num][0] <= arrival_time <= purdue_BOG_EOG[s_num][1])
                percent = count / sum(len(data_[1]) for data_ in seed_data)
                percent_on_green_set.append(percent)
                # print(f'随机种子为{seed}下，交叉口{s_num}的POG为：{round(percent * 100, 2)}%')

        # print(f'随机种子为{seed}下平均POG为：{round((sum(percent_on_green_set) / len(percent_on_green_set)) * 100, 2)}%')
    if len(percent_on_green_set) != 0:
        POG_final = round((sum(percent_on_green_set) / len(percent_on_green_set)) * 100, 2)
    else:
        POG_final = 0
    print('============================================================================')
    print(f'The current data average POG is:{POG_final}%')
    print('============================================================================')

    return POG_final / 100


#  output Stop Percent
def output_stop_percent(inter_location: list, trajectories_data: dict, stop_speed_threshold: float) -> float:
    """
    输出当前路线停车率, 忽略第一个交叉口产生的停车
    :param inter_location: 交叉口位置信息 -> list[float]
    :param trajectories_data: 轨迹数据 -> dict{seed: tuple[list[list[stamp_ID]]]}
    :param stop_speed_threshold: 停车速度阈值 -> float
    :return: stop_percent -> float
    """
    stop_percent = []  # 存储所有层级下的stop_percent

    for seed, single_data in trajectories_data.items():  # 读取随机种子层数据
        count = 0  # 初始化计数器

        for stamp_ID in range(len(single_data[1])):
            distance_stamp_ID, speed_stamp_ID = single_data[1][stamp_ID], single_data[2][stamp_ID]
            # 找到第一个交叉口的元素的索引
            index = next((i for i, dis in enumerate(distance_stamp_ID) if dis > inter_location[0]), None)
            del speed_stamp_ID[:index + 1]  # index+1因为要删除索引处的元素
            count += 1 if any(speed <= stop_speed_threshold for speed in speed_stamp_ID) else 0

        stop_percent.append(count / len(single_data[1]))
        # print(f'随机种子为{seed}时，停车率为：{round((count / len(single_data[1])) * 100, 2)}%')
    print('============================================================================')
    print(f'The current average stop ratio for the data is: {round((sum(stop_percent) / len(stop_percent)) * 100, 2)}%')
    print('============================================================================')

    return sum(stop_percent) / len(stop_percent)


# output average speed
def output_average_speed(single_rate_data: dict, filename: str, path: str):
    """
    输出.csv文件
    :param single_rate_data: 单向评价数据，从RateData类获取 -> dict
    :param filename: 文件名 如：'avespeed' -> str
    :param path: 文件位置 -> str
    :return: None
    """
    avespeed_set = []

    def write_list_to_csv(input_list, filename_='output.csv', path_='.'):
        # 确保路径存在
        if not os.path.exists(path_):
            os.makedirs(path_)
        # 构建完整的文件路径
        full_path = os.path.join(path_, filename_)

        with open(full_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            # 将列表作为单列写入CSV文件
            for item in input_list:
                writer.writerow([item])

    for seed, single_bound_data in single_rate_data.items():
        for rate_ID in single_bound_data:
            avespeed_set.append(round(rate_ID[2], 4))

    write_list_to_csv(avespeed_set, filename_=f'{filename}.csv', path_=path)


def output_seed_speed(avespeed_data: dict, filename: str, path: str):
    """
    输出.csv文件
    :param avespeed_data: 单向评价数据，从RateData类获取 -> dict
    :param filename: 文件名 如：'avespeed' -> str
    :param path: 文件位置 -> str
    :return: None
    """
    avespeed_set = []

    def write_list_to_csv(input_list, filename_='output.csv', path_='.'):
        # 确保路径存在
        if not os.path.exists(path_):
            os.makedirs(path_)
        # 构建完整的文件路径
        full_path = os.path.join(path_, filename_)

        with open(full_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            # 将列表作为单列写入CSV文件
            for item in input_list:
                writer.writerow([item])

    for seed, avespeed in avespeed_data.items():
        avespeed_set.append(round(avespeed, 4))

    write_list_to_csv(avespeed_set, filename_=f'{filename}.csv', path_=path)


# output vehicle stop delay
def output_stop_delay(single_rate_data: dict, inter_num: int, filename: str, path: str):
    """
    输出.csv文件
    :param single_rate_data: 单向评价数据，从RateData类获取 -> dict
    :param inter_num: 交叉口个数 -> int
    :param filename: 文件名 如：'stop delay -> str
    :param path: 文件位置 -> str
    :return: None
    """
    delaySet, seed_delay = [], []

    def write_list_to_csv(input_data, filename_='output.csv', path_='.', stamp='all_veh'):
        # 确保路径存在
        if not os.path.exists(path_):
            os.makedirs(path_)
        # 构建完整的文件路径
        full_path = os.path.join(path_, filename_)

        # 打开文件，准备写入
        with open(full_path, 'w', newline='', encoding='utf-8') as csvfile:
            if stamp == 'all_veh':
                # 创建CSV写入器
                writer = csv.writer(csvfile)
                # 写入表头
                num_cols = len(input_data[0]) if input_data else 0
                headers = [f"Start to end {n + 1}th intersection" for n in range(num_cols)]
                writer.writerow(headers)
                for row in input_data:
                    writer.writerow(row)
            else:
                writer = csv.writer(csvfile)
                # 将列表作为单列写入CSV文件
                for item in input_data:
                    writer.writerow([item])

    stop_times = 0  # 计算停车次数
    num_veh = 0  # 计算干线车辆数
    for seed, single_bound_data in single_rate_data.items():
        s_dealy_temp = []
        num_veh += len(single_bound_data)  # 计算种子干线车辆数
        for rate_ID in single_bound_data:
            delay_set = []
            stopdelay = rate_ID[0]
            for i in range(1, inter_num + 1):
                sum_inter_delay = []
                for key, value in stopdelay.items():
                    if value == i:
                        sum_inter_delay.append(key)
                        if i > 1:
                            stop_times += 1
                    else:
                        sum_inter_delay.append(0)

                delay_set.append(round(sum(sum_inter_delay), 4))
                s_dealy_temp.append(round(sum(sum_inter_delay), 4))
            delaySet.append(delay_set)

        seed_delay.append(round(sum(s_dealy_temp) / len(s_dealy_temp), 4))
    np.array(delaySet)
    np.array(seed_delay)
    print('The average number of stops is:', round(stop_times / ((inter_num - 1) * num_veh)), 2)
    print('The number of arterial vehicles is:', num_veh)
    write_list_to_csv(delaySet, filename_=f'{filename}_veh_delay.csv', path_=path, stamp='all_veh')
    write_list_to_csv(seed_delay, filename_=f'{filename}_seed_avedelay.csv', path_=path, stamp='all_seed')


class RateCoordinationPerformance:
    """
    为了简洁化
    这里参数初始化做了合并处理，即使用tuple方式 -> (inbound_data, outbound_data)
    因此在输入时以元组数据类型将双向评价数据合并后直接输入
    最后调用 determine_rate()
    """

    def __init__(self, rate_data: tuple[dict, dict] = None, inter_location: tuple[list, list] = None,
                 inter_traffic_volume: tuple[list, list] = None, ari_traffic_volume: tuple[int, int] = None,
                 lane_arterial: tuple[list, list] = None, lane_side: list = None,
                 ari_signal_plan_ring: tuple[Any, Any] = None, cycle: list = None,
                 saturation_flow_rate: int = 1800, lim_speed=50,
                 dimensionless_constants: list = None):
        """
        Initialize the data.
        :param rate_data: from class ratedata gets rate_data, including speed data and stopping data.
        :param inter_traffic_volume: average hourly traffic volume in both directions of intersection.
        :param ari_traffic_volume: average hourly traffic volume in both directions along the arterial.
        :param lane_arterial: the total number of lanes in the arterial direction at the ath intersection.
        :param lane_side: the total number of lanes in the side street at the ath intersection.
        :param ari_signal_plan_ring: signal timing plan ring. -> (ring1, ring2)
        :param saturation_flow_rate: the saturation traffic flow rate (vphpl), typically 1800 vphpl.
        :param cycle: intersection cycle.
        :param lim_speed: posted limited speed.
        :param dimensionless_constants: non-dimensional calibration parameters, representing the impacts of different
                                        intersection types on the ideal progressive speed.
        """
        if rate_data is not None:
            self.inbound_rate_data, self.outbound_rate_data = rate_data
        if inter_location is not None:
            self.inbound_inter_location, self.outbound_inter_location = inter_location
        if inter_traffic_volume is not None:
            self.inbound_inter_volume, self.outbound_inter_volume = inter_traffic_volume
        if ari_traffic_volume is not None:
            self.inbound_ari_volume, self.outbound_ari_volume = ari_traffic_volume
        if ari_signal_plan_ring is not None:
            self.ari_signal_plan_ring1, self.ari_signal_plan_ring2 = ari_signal_plan_ring
        if lane_side is not None:
            self.inbound_n_side, self.outbound_n_side = lane_side, lane_side
        if lane_arterial is not None:
            self.inbound_n_arterial, self.outbound_n_arterial = lane_arterial
        self.cycle = cycle
        self.lim_speed = lim_speed
        self.weight = (1, 1)
        self.saturation_flow_rate = saturation_flow_rate
        if dimensionless_constants is None:
            dimensionless_constants = [0.85, 0.9, 0.95, 1, 1]
        self.dimensionless_constants = dimensionless_constants

    @staticmethod
    def _create_container(container_type) -> Union[dict[Any, Any], list[Any]]:
        if container_type == 'dict':
            return {}
        elif container_type == 'list':
            return []
        else:
            raise ValueError("Unsupported container type. Use 'dict' or 'list'.")

    # 确定交叉口分类
    def _arterial_VC_ratio(self, index, green_time, inter_traffic_volume, n_arterial) -> float:
        ratio = (inter_traffic_volume[index] / (n_arterial[index] * green_time[index])) * (
                self.cycle[index] / self.saturation_flow_rate)
        return ratio

    # 根据Arterial_V_C_Ratio和n_side[i]的值确定交叉口类型
    @staticmethod
    def _determine_intersection_type(ratio, n_side):
        n_index, ari_index = None, None
        # 定义交叉口类型映射
        intersection_types = np.mat([
            [5, 4, 3, 2],
            [4, 3, 2, 1],
            [2, 2, 1, 1]
        ])
        ratio_ranges = {
            (0, 0.3): 0,
            (0.3, 0.55): 1,
            (0.55, 0.85): 2,
            (0.85, 1): 3,
        }
        n_side_ranges = {
            (0, 3): 0,
            (3, 7): 1,
            (7, float('inf')): 2,
        }
        for (low, high), index in ratio_ranges.items():
            if low < ratio <= high:
                ari_index = index
            elif ratio == 0:
                ari_index = 0
        for (low, high), index in n_side_ranges.items():
            if low < n_side <= high:
                n_index = index
            elif n_side == 0:
                n_index = 0
        return intersection_types[n_index, ari_index]

    def classification(self, inter_traffic_volume: list, n_arterial: list, n_side: list,
                       ari_signal_plan_ring: Any) -> list:
        """
        计算交叉口类别
        :param ari_signal_plan_ring: signal timing plan ring.
        :param inter_traffic_volume: average hourly traffic volume in the direction.
        :param n_arterial: the total number of lanes in the arterial direction at the ath intersection.
        :param n_side: the total number of lanes in the side street at the ath intersection.
        :return: Intersection Classifications
        """
        type_intersection = self._create_container('list')
        # 计算干线方向绿灯时间 through green time + left green time
        if type(ari_signal_plan_ring) is dict:
            green_time = [i + j for i, j in zip(ari_signal_plan_ring['green1'], ari_signal_plan_ring['green2'])]
        else:
            g_time = []
            for n in range(len(ari_signal_plan_ring)):
                g_t = [i + j for i, j in zip(ari_signal_plan_ring[n]['green1'], ari_signal_plan_ring[n]['green2'])]
                g_time.append(g_t)
            # 使用 zip(*green_time) 转置列表，然后逐列计算平均值
            green_time = [sum(col) / len(col) for col in zip(*g_time)]
        if any(isinstance(x, list) for x in self.cycle):
            self.cycle = [sum(cycle) / len(cycle) for cycle in self.cycle]

        for i in range(len(self.cycle)):
            ratio = self._arterial_VC_ratio(i, green_time, inter_traffic_volume, n_arterial)
            # 根据n_side[i]的值选择交叉口类型
            type_intersection.append(self._determine_intersection_type(ratio, n_side[i]))

        return type_intersection

    # 计算attainability of ideal progression得分
    @staticmethod
    def _get_ideal_progression_speed(free_flow_speed: float, var: list, IC_num: list) -> float:
        return free_flow_speed * max(((var[0] ** IC_num[0]) * (var[1] ** IC_num[1]) * (var[2] ** IC_num[2]) * (
                var[3] ** IC_num[3]) * (var[4] ** IC_num[4])), 0.5)

    def get_AIP_score(self, lim_speed: float, ave_speed: float, type_intersection: list):
        """
        attainability of ideal progression.
        :param type_intersection: IC types
        :param lim_speed: posted limited speed.
        :param ave_speed: vehicle average speed when drive in arterial direction.
        :return: AIP_score
        """
        IC_type_num = self._create_container('list')
        for i in range(1, 6):
            N_i = type_intersection.count(i)
            IC_type_num.append(N_i)
        var = self.dimensionless_constants
        free_flow_speed = lim_speed * 0.62 + 5  # 自由流动速度，等于限速 +5
        AvrSpeed = ave_speed * 0.62  # 平均速度
        ideal_progression_speed = self._get_ideal_progression_speed(free_flow_speed, var, IC_type_num)
        AIP_Score = min((AvrSpeed / ideal_progression_speed) * 100, 100)

        return AIP_Score

    # 计算attainability of user satisfaction得分
    def _get_stop_equivalency(self, stop_time: dict, type_intersection: list) -> dict[int, float]:
        stop_time = {k: v for k, v in stop_time.items() if v != 1}  # 删除第一个交叉口的停车信息
        stop_equivalency = self._create_container('dict')  # 生成轨迹stop_equivalency容器
        for stime, s_num in stop_time.items():
            if stime < 3:
                se_inter = 0
            elif 3 <= stime < 10:
                se_inter = 0.5
            else:  # 10 <= stime
                fan = 0
                if type_intersection[s_num - 1] == 1:
                    fan = 0.5
                elif type_intersection[s_num - 1] == 2 or type_intersection[s_num - 1] == 3:
                    fan = 0.25
                elif type_intersection[s_num - 1] == 4 or type_intersection[s_num - 1] == 5:
                    fan = 0.15

                se_inter = 0.5 + (stime - 10) / (fan * self.cycle[s_num - 1])

            if s_num in stop_equivalency:
                stop_equivalency[s_num] += se_inter
            else:
                stop_equivalency.setdefault(s_num, se_inter)

        return stop_equivalency  # {第s_num个交叉口：stop_equivalency_value}

    def _get_stop_equivalency_per_intersection(self, stop_equivalency: dict, stop_distance: dict) -> float:
        spi_container = self._create_container('list')  # 生成轨迹SPI容器
        stop_distance = {k: v for k, v in stop_distance.items() if k != 1}  # 删除第一个交叉口的停车信息
        for s_num, se in stop_equivalency.items():
            spi_container.append(se * max(0.1 / (0.00062137 * stop_distance[s_num]), 1))
        if len(spi_container) != 0:
            return 100 * sum(spi_container) / len(spi_container)
        else:
            return 0

    def get_AUS_score(self, stop_time: dict, stop_distance: dict, type_intersection: list) -> float:
        """
        attainability of user satisfaction.
        :param type_intersection: Intersection Classifications Types for each intersection
        :param stop_time: vehicle stop time in arterial direction.
        :param stop_distance: stop distance between two stops of the vehicle on the trajectory.
        :return: AUS_score

        stop_time: dict = {stop_delay: inter_num}    key -> float  value -> int
        inter_num: 第 inter_num 个交叉口 -> int
        stop_distance: dict = {inter_num：stop_distance_interval}    key -> int  value -> float
        """
        stop_equivalency = self._get_stop_equivalency(stop_time, type_intersection)
        SPI = self._get_stop_equivalency_per_intersection(stop_equivalency, stop_distance)
        AUS_Score = 100 - (50 / (1 + math.exp(-(SPI * 2 - 65) / 10)))

        return AUS_Score

    # 获取system average cycle length
    def get_SACL(self) -> int:
        sacl = sum(self.cycle) / len(self.cycle)
        if sacl <= 70:
            adjust_sacl_value = 5
        elif 90 >= sacl > 70:
            adjust_sacl_value = 2
        elif 140 >= sacl > 90:
            adjust_sacl_value = 0
        elif 160 >= sacl > 140:
            adjust_sacl_value = -2
        else:
            adjust_sacl_value = -5

        return adjust_sacl_value

    # 获取proportion of number of close-spacing intersections
    @staticmethod
    def get_PCSI(inter_location: list) -> int:
        # 计算交叉口间距
        spacing_inter = [(inter_location[i + 1] - inter_location[i]) * 3.28 for i in range(len(inter_location) - 1)]
        proportion_close_spacing_inter = sum(1 for spacing in spacing_inter if spacing <= 1000) / len(inter_location)

        if 0 < proportion_close_spacing_inter <= 0.25:
            adjust_pcsi_value = 0
        elif 0.5 >= proportion_close_spacing_inter > 0.25:
            adjust_pcsi_value = 1
        elif 0.5 >= proportion_close_spacing_inter > 0.75:
            adjust_pcsi_value = 2
        elif 1 >= proportion_close_spacing_inter > 0.75:
            adjust_pcsi_value = 4
        else:
            adjust_pcsi_value = 0

        return adjust_pcsi_value

    # 计算调整值
    @staticmethod
    def aggregate_score(AIP_Score: float, AUS_Score: float, adjust_sacl_value: int, adjust_pcsi_value: int) -> tuple:

        aggregateAIP_score = AIP_Score + adjust_sacl_value + adjust_pcsi_value
        aggregateAUS_score = AUS_Score + adjust_sacl_value + adjust_pcsi_value

        return aggregateAIP_score, aggregateAUS_score

    # 单向评级
    @staticmethod
    def single_direction_performance(aggregateAIP_score: float, aggregateAUS_score: float) -> str:
        # 定义分数段对应的等级
        grade = np.mat([
            ['A', 'A', 'B', 'C', 'N/A'],
            ['A', 'B', 'B', 'C', 'N/A'],
            ['B', 'B', 'C', 'D', 'N/A'],
            ['C', 'C', 'D', 'D', 'F'],
            ['F', 'F', 'F', 'F', 'F']
        ])

        def get_grade(score):
            score_ranges = {
                (-float('inf'), 60): 4,
                (60, 70): 3,
                (70, 80): 2,
                (80, 90): 1,
                (90, float('inf')): 0
            }
            for (low, high), index in score_ranges.items():
                if low < score <= high:
                    return index
            return None  # 如果没有找到对应的区间，返回None

        # 获取AUS和AIP的等级
        aus_index = get_grade(aggregateAUS_score)
        aip_index = get_grade(aggregateAIP_score)

        return grade[aus_index, aip_index]

    def get_RPF(self) -> float:
        rpf = self._create_container('list')
        volume = [self.inbound_ari_volume, self.outbound_ari_volume]
        for i in range(2):
            rpf.append(self.weight[i] * volume[i] / sum(volume))

        return max(rpf)

    # 确定最终评级
    @staticmethod
    def performance_and_description():
        arterial_performance1 = np.mat(
            [['A', 'A', 'C', 'C', 'F'],
             ['A', 'B', 'C', 'C', 'F'],
             ['B', 'C', 'C', 'D', 'F'],
             ['C', 'C', 'D', 'D', 'F'],
             ['F', 'F', 'F', 'F', 'F']])
        arterial_performance2 = np.mat(
            [['A', 'B', 'B', 'C', 'F'],
             ['A', 'B', 'C', 'D', 'F'],
             ['B', 'B', 'C', 'D', 'F'],
             ['C', 'C', 'D', 'D', 'F'],
             ['F', 'F', 'F', 'F', 'F']])
        arterial_performance3 = np.mat(
            [['A', 'B', 'C', 'D', 'F'],
             ['A', 'B', 'C', 'D', 'F'],
             ['A', 'B', 'C', 'D', 'F'],
             ['B', 'C', 'C', 'D', 'F'],
             ['C', 'D', 'F', 'F', 'F']])

        Description = {'A': 'Excellent performance, no need for re-timing.',
                       'B': 'Good performance, minor adjustments could be made.',
                       'C': 'Average performance, re-timing could significantly improve the operations.',
                       'D': 'Below-average performance, re-timing is strongly recommended.',
                       'F': 'Poor performance, re-timing is urgently needed.'}
        return arterial_performance1, arterial_performance2, arterial_performance3, Description

    def determine_rate(self, route_grade: list, RPF: float) -> Union[tuple[str, str], tuple[Optional[Any], Any]]:
        grade = None
        Minor = ['A', 'B', 'C', 'D', 'F']
        Major = ['A', 'B', 'C', 'D', 'F']
        arterial_performance1, arterial_performance2, \
            arterial_performance3, Description = self.performance_and_description()
        if 'N/A' in route_grade:
            return 'N/A', 'Poor performance, re-timing is urgently needed.'
        else:
            if 0.7 > RPF >= 0.5:
                grade = arterial_performance1[Major.index(route_grade[1]), Minor.index(route_grade[0])]
            elif 0.9 > RPF >= 0.7:
                grade = arterial_performance2[Major.index(route_grade[1]), Minor.index(route_grade[0])]
            elif 1.0 > RPF >= 0.9:
                grade = arterial_performance3[Major.index(route_grade[1]), Minor.index(route_grade[0])]
            return grade, Description[grade]

    # 计算平均停车时间
    def get_avestop_time(self):
        pass

    # output performance grade
    def _calculate_single_performance(self, rate_data: dict, IC_types: list, inter_location: list) -> tuple:
        # AUS score 数据集合 AIP score 数据集合
        aus_score_set, aip_score_set = self._create_container('list'), self._create_container('list')
        ave_speed, ave_speed_seed = self._create_container('list'), self._create_container('dict')
        for seed, data in rate_data.items():  # read seed data
            ave_speed_seed.setdefault(seed, [])
            for trajectory_ID in data:  # read vehicle data
                ave_speed.append(trajectory_ID[2])
                ave_speed_seed[seed].append(trajectory_ID[2])
                # 调用计算AIP AUS
                aip = self.get_AIP_score(self.lim_speed, trajectory_ID[2], IC_types)
                aus = self.get_AUS_score(trajectory_ID[0], trajectory_ID[1], IC_types)
                # 计算调整值
                sacl = self.get_SACL()
                pcsi = self.get_PCSI(inter_location)
                # 计算调整AIP AUS
                aggregate_aip, aggregate_aus = self.aggregate_score(aip, aus, sacl, pcsi)
                aip_score_set.append(aggregate_aip)
                aus_score_set.append(aggregate_aus)
        return aus_score_set, aip_score_set, sum(ave_speed) / len(ave_speed), ave_speed_seed

    @staticmethod
    def _seed_ave_speed(ave_speed_seed: dict):
        for key in ave_speed_seed:
            ave_speed_seed[key] = sum(ave_speed_seed[key]) / len(ave_speed_seed[key])  # 更新列表为平均值
        return ave_speed_seed

    @staticmethod
    def convert_ring(ring_data: dict) -> dict:
        """
        将ARI信号配时环1格式转换为环2格式
        """
        # 初始化目标数据结构
        ring = {
            'yr1': [],
            'green1': [],
            'yr2': [],
            'green2': [],
            'red': []
        }

        # 按相位顺序处理数据（S1 -> S4）
        for phase in sorted(ring_data.keys()):
            values = ring_data[phase]

            # 解包并填充数据（验证列表长度）
            if len(values) != 5:
                raise ValueError(f"相位 {phase} 的数据长度不正确，预期5个元素，实际得到{len(values)}个")

            ring['yr1'].append(values[0])  # 黄红灯时间1
            ring['green1'].append(values[1])  # 绿灯时间1
            ring['yr2'].append(values[2])  # 黄红灯时间2
            ring['green2'].append(values[3])  # 绿灯时间2
            ring['red'].append(values[4])  # 全红时间

        return ring

    def convert_adapt_ring(self, adapt_ring_data: list) -> list:
        """
        输出感应条件配时数据转换
        :param adapt_ring_data: 配时数据
        :return: 转换配时数据
        """
        for i in range(len(adapt_ring_data)):
            if set(adapt_ring_data[i].keys()) != {'yr1', 'green1', 'yr2', 'green2', 'red'}:  # 格式转换
                adapt_ring_data[i] = self.convert_ring(adapt_ring_data[i])
        return adapt_ring_data

    def convert_signalplan(self) -> Any:
        ari_signal_plan_ring1, ari_signal_plan_ring2 = None, None
        if type(self.ari_signal_plan_ring1) is dict:
            if set(self.ari_signal_plan_ring1.keys()) != {'yr1', 'green1', 'yr2', 'green2', 'red'}:  # 格式转换
                ari_signal_plan_ring1 = self.convert_ring(self.ari_signal_plan_ring1)
                ari_signal_plan_ring2 = self.convert_ring(self.ari_signal_plan_ring2)
        if type(self.ari_signal_plan_ring1) is list:
            ari_signal_plan_ring1 = self.convert_adapt_ring(self.ari_signal_plan_ring1)
            ari_signal_plan_ring2 = self.convert_adapt_ring(self.ari_signal_plan_ring2)

        return ari_signal_plan_ring1, ari_signal_plan_ring2

    def output_performance_grade(self, path='.\\ave_speed_seed\\') -> tuple:
        """
        输出最终评级
        :param path: 每个随机种子下车辆对应平均速度，需要输出则设置path
        :return: in_ave_speed_seed, out_ave_speed_seed, grade, description
        """
        # 格式更新
        if (result := self.convert_signalplan()) != (None, None):
            self.ari_signal_plan_ring1, self.ari_signal_plan_ring2 = result
        # inbound
        # 计算交叉口类型
        IC_types: list = self.classification(self.inbound_inter_volume, self.inbound_n_arterial, self.inbound_n_side,
                                             self.ari_signal_plan_ring1)
        aus_score_set, aip_score_set, \
            ave_speed, in_ave_speed_seed = self._calculate_single_performance(self.inbound_rate_data, IC_types,
                                                                              self.inbound_inter_location)
        # inbound 评级
        inbound_ave_aip_score = sum(aip_score_set) / len(aip_score_set)
        inbound_ave_aus_score = sum(aus_score_set) / len(aus_score_set)
        in_grade = self.single_direction_performance(inbound_ave_aip_score, inbound_ave_aus_score)
        # 求种子平均速度
        in_ave_speed_seed = self._seed_ave_speed(in_ave_speed_seed)
        print('============================================================================')
        print('inbound average speed under each random seed in the direction is:', in_ave_speed_seed)
        print('inbound average speed in the direction is:', round(ave_speed, 2))
        print('inbound direction ave_aip_score is:', round(inbound_ave_aip_score, 2))
        print('inbound direction ave_aus_score is:', round(inbound_ave_aus_score, 2))
        print('inbound directional Arterial Coordination performance level is:', in_grade)
        # outbound
        # 计算交叉口类型
        IC_types: list = self.classification(self.outbound_inter_volume, self.outbound_n_arterial, self.outbound_n_side,
                                             self.ari_signal_plan_ring2)
        aus_score_set, aip_score_set, \
            ave_speed, out_ave_speed_seed = self._calculate_single_performance(self.outbound_rate_data, IC_types,
                                                                               self.outbound_inter_location)
        # outbound 评级
        outbound_ave_aip_score = sum(aip_score_set) / len(aip_score_set)
        outbound_ave_aus_score = sum(aus_score_set) / len(aus_score_set)
        out_grade = self.single_direction_performance(outbound_ave_aip_score, outbound_ave_aus_score)
        # 求种子平均速度
        out_ave_speed_seed = self._seed_ave_speed(out_ave_speed_seed)
        print('-------------------------------------------------------------------------')
        print('outbound average speed under each random seed in the direction is:', out_ave_speed_seed)
        print('outbound average speed in the direction is:', ave_speed)
        print('outbound direction ave_aip_score is:', outbound_ave_aip_score)
        print('outbound direction ave_aus_score is:', outbound_ave_aus_score)
        print('outbound directional Arterial Coordination performance level is:', out_grade)
        print('============================================================================')

        output_seed_speed(in_ave_speed_seed, 'inbound_seed_ave_speed', path)
        output_seed_speed(out_ave_speed_seed, 'outbound_seed_ave_speed', path)

        # 干线整体评级
        rpf = self.get_RPF()
        grade, description = self.determine_rate([in_grade, out_grade], rpf)
        print("The final rating for arterial coordination performance is:", grade)
        print(description)
        print('============================================================================')

        return in_ave_speed_seed, out_ave_speed_seed, grade, description


if __name__ == '__main__':
    print('output grade of arterial signal coordination')
