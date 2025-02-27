"""
用于基于轨迹数据解析干线协调评级所需数据

Author: CheneyZhao.wust.edu
           cheneyzhao@126.com
"""
from typing import Union, Any


class RateData:

    def __init__(self, trajectories_data: dict, inter_location: list, stop_speed_threshold: float,
                 sum_length_outbound=None):
        """
        初始化轨迹数据分析
        :param trajectories_data: 单向轨迹数据 -> dict
        :param inter_location: 交叉口位置 注：这里按照单向停止线位置为基准 -> list
        :param stop_speed_threshold: 车辆停车速度阈值(km/h) -> float
        :param sum_length_outbound: 如果需要输出反向（outbound）, 需要输入反向的路径长度（m），
               两个选项：
                    从vis-sim的路段长度导出lanelength_outbound，则该参数类型为列表 -> list
                    直接输入，则该参数类型为浮点型 -> float
        """
        self.stop_speed_threshold = stop_speed_threshold
        self.trajectories_data = trajectories_data
        # 判断方向
        if sum_length_outbound is not None:
            if type(sum_length_outbound) == list:
                self.sum_length_outbound = sum(sum_length_outbound)
            elif type(sum_length_outbound) == float:
                self.sum_length_outbound = sum_length_outbound
            inter_location.reverse()
            for i in range(len(inter_location)):
                inter_location[i] = self.sum_length_outbound - inter_location[i]
        # 在距离停止线20m处设置虚拟检测器
        self.inter_location = [i + 20 for i in inter_location]
        self.inter_location.insert(0, 0)

    # 计算平均速度
    def get_avespeed(self, distance_stamp: list, speed_stamp: list) -> float:
        index = next(i for i, dis in enumerate(distance_stamp) if dis > self.inter_location[1] + 100)
        return sum(speed_stamp[index:]) / len(speed_stamp[index:])

    # 获取停车时间
    def _get_index(self, speed_stamp: list) -> list:
        # 初始化变量
        threshold_index_set = self._create_container('list')
        in_threshold_segment = False
        index_first = None

        # 遍历ID轨迹speed_stamp
        for index, value in enumerate(speed_stamp):
            if value <= self.stop_speed_threshold:
                if not in_threshold_segment:  # 如果当前不在stop_speed_threshold的片段中
                    in_threshold_segment = True
                    index_first = index  # 记录第一个stop_speed_threshold的位置

            # 如果当前在threshold的片段中且当前值不是threshold
            elif in_threshold_segment and value > self.stop_speed_threshold:
                in_threshold_segment = False
                index_end = index - 1  # 记录最后一个0的位置
                threshold_index_set.append((index_first, index_end))  # 添加元组到列表

        # 检查是否以stop_speed_threshold结束
        if in_threshold_segment:
            threshold_index_set.append((index_first, len(speed_stamp) - 1))

        # 打印结果
        # print("产生停车的索引位置:", threshold_index_set)

        return threshold_index_set

    def _find_intersection_info(self, stop_loction: float):

        if stop_loction < self.inter_location[0] or stop_loction >= self.inter_location[-1]:
            return None
        for i in range(len(self.inter_location) - 1):
            start = self.inter_location[i]
            end = self.inter_location[i + 1]
            if start <= stop_loction < end:
                return i + 1  # 返回交叉口信息
        raise IndexError("Wrong position: The numbers are not in any intervals.")

    def get_stop_time(self, speed_stamp: list, time_stamp: list, distance_stamp: list) -> dict:

        stop_time = self._create_container('dict')  # 生成停车时间数据,停车距离数据存储容器
        index_set: list = self._get_index(speed_stamp)  # 获取速度低于阈值的节点位置索引
        for index in index_set:
            stime: float = time_stamp[index[1]] - time_stamp[index[0]]
            stop_loction: float = distance_stamp[index[1]]
            # 获取停车位置交叉口信息
            inter_num: int = self._find_intersection_info(stop_loction)
            # 存储数据
            if inter_num is not None:
                stop_time.setdefault(stime, inter_num)

        return stop_time  # {value: inter_num}  value: 停车时长 inter_num: 第i个交叉口

    # 获取两次停车间距
    def _get_stop_distance(self, stop_location_set: list) -> dict:
        stop_distance, value_counts = self._create_container('dict'), self._create_container('dict')
        # 统计每个第二个元素出现的次数
        for item in stop_location_set:
            _, value = item
            if value in value_counts:
                value_counts[value] += 1
            else:
                value_counts[value] = 1

        # 将唯一值的第一个元素变成100000并更新字典b
        for item in stop_location_set:
            _, value = item
            if value_counts[value] == 1:
                item[0] = 10000
                stop_distance.setdefault(value, 10000)  # 计算差值并更新字典b

        judge_list = self._create_container('list')
        for i in range(len(stop_location_set) - 1):
            current = stop_location_set[i]
            next_item = stop_location_set[i + 1]
            if current[1] == next_item[1]:
                c = next_item[0] - current[0]
                judge_list.append([next_item[1], c])

        if len(judge_list) != 0:
            result = self._create_container('list')
            for sublist in judge_list:
                # 检查子列表的第一个元素是否已经存在于 result 中
                existing_sublist = next((x for x in result if x[0] == sublist[0]), None)
                if existing_sublist is None:
                    # 如果不存在，直接添加到 result 中
                    result.append(sublist)
                else:
                    # 如果存在，比较第二个元素，保留最小的那个
                    if sublist[1] < existing_sublist[1]:
                        result.remove(existing_sublist)
                        result.append(sublist)

            for sublist in result:
                stop_distance.setdefault(sublist[0], sublist[1])

        stop_distance_ = dict(sorted(stop_distance.items()))

        return stop_distance_

    def get_stop_distance_interval(self, speed_stamp: list, distance_stamp: list) -> dict:
        # 生成停车时间数据,停车距离数据存储容器
        stop_distance, stop_location_set = self._create_container('dict'), self._create_container('list')
        index_set: list = self._get_index(speed_stamp)  # 获取速度低于阈值的节点位置索引
        for index in index_set:
            stop_location: float = distance_stamp[index[1]]
            # 获取停车位置交叉口信息
            inter_num: int = self._find_intersection_info(stop_location)
            """
            {stop_location: 1, stop_location: 1, stop_location: 2, stop_location: 3, stop_location: 3}
            if num stop_location == 1 or 0:
                stop_distance_interval = +∞
            else:
                stop_distance_interval = calculate interval()
            """
            if inter_num is not None:
                stop_location_set.append([stop_location, inter_num])

        stop_distance = self._get_stop_distance(stop_location_set)

        return stop_distance

    @staticmethod
    def _create_container(container_type) -> Union[dict[Any, Any], list[Any]]:
        if container_type == 'dict':
            return {}
        elif container_type == 'list':
            return []
        else:
            raise ValueError("Unsupported container type. Use 'dict' or 'list'.")

    # 获取评价数据
    def output_rate_data(self) -> dict:
        """
        轨迹数据格式：

        方向数据集合： trajectory_data: dict = {"seed": single_data, ...}

        单次仿真轨迹数据集合：
                         single_data: list = [[list[time_stamp], list[distance_stamp], list[speed_stamp]],
                                               ...
                                               ...                                                         ]
        干线车辆轨迹数据:
                        list[list[time_stamp_ID], ...],
                        list[list[distance_stamp_ID], ...],
                        list[list[speed_stamp_ID], ...]
        :return: rate_data
                        输出数据格式：
                        rate_data： dict{"seed": single_inbound_data, ...}

                        single_data: list = [[dict[stop_time], dict[stop_distance], ave_speed], ...]

                        stop_time: dict = {stop_delay: inter_num}
                                   key -> float  value -> int

                        stop_distance: dict = {stop_distance_interval: inter_num}
                                       key -> float  value -> int

                        ave_speed: float
        """
        # 生成评价数据存储容器
        rate_data: dict = self._create_container('dict')
        for seed, trajectory in self.trajectories_data.items():
            # 生成ID评价数据存储容器
            single_data: list = self._create_container('list')

            # 读取同一随机种子下车辆ID轨迹数据
            time_stamp_set, distance_stamp_set, speed_stamp_set = trajectory

            # 读取车辆ID轨迹数据
            for i in range(len(time_stamp_set)):
                # print('===============================speed_stamp_set[i]===========================================')
                # print(speed_stamp_set[i])
                # print('===============================speed_stamp_set[i]===========================================')
                # 计算车辆ID轨迹平均速度
                ave_speed: float = self.get_avespeed(distance_stamp_set[i], speed_stamp_set[i])
                """
                # {calculate_value: inter_num}  calculate_value: 停车时长 inter_num: 第i个交叉口 
                                                -> 从车辆起点到终点途径的交叉口，outbound需要逆向处理
                """
                # 计算车辆ID轨迹停车时间数据
                stop_time: dict = self.get_stop_time(speed_stamp_set[i], time_stamp_set[i], distance_stamp_set[i])
                # 计算车辆ID轨迹停车距离数据
                stop_distance: dict = self.get_stop_distance_interval(speed_stamp_set[i], distance_stamp_set[i])

                # ID轨迹数据对应评价数据
                single_data.append([stop_time, stop_distance, ave_speed])
            # 同一随机种子下评价数据放入容器
            rate_data.setdefault(seed, single_data)

        return rate_data


if __name__ == "__main__":
    print('used for output rate data')
