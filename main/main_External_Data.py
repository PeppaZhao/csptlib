# A case study is used to describe how external data can be used to evaluate the coordination performance level of
# arterial. For any inquiries, please contact Cheney Zhao at cheneyzhao@126.com. This software is the intellectual
# property of Cheney Zhao at WUST (Wuhan University of Science and Technology).
# Data acquisition address: https://pan.baidu.com/s/17jS1it-PGllnUC-5981BOA?pwd=LTWA


from systrajectorylib.rateperformance import RateCoordinationPerformance, output_stop_delay, output_POG, \
    output_stop_percent
from systrajectorylib.rateperformance import output_average_speed
from datastore import load_variavle, AterialDataCollection
from transplotlib import SignalPlanPlot, PurduePlot, transplt


def exp():
    # ////////////////////////////数据准备//////////////////////////////////////////////////////
    # 交叉口位置信息
    inter_location_inbound = [154.42, 1271.24, 1998.41, 2580.95]
    inter_location_outbound = [202.49, 1347.52, 2083.13, 2683.34]
    # 读取轨迹数据
    intbound_tradata = load_variavle(f'D:\\CSPT\\TrajectoryData\\inbound_trajectorydata.pkl')
    outbound_tradata = load_variavle(f'D:\\CSPT\\TrajectoryData\\outbound_trajectorydata.pkl')
    inbound_rate_data = load_variavle(f'D:\\CSPT\\RateData\\inbound_rate_data.pkl')
    outbound_rate_data = load_variavle(f'D:\\CSPT\\RateData\\outbound_rate_data.pkl')
    # ////////////////////////////////////////////////////////////////////////////////////////

    # /////////////////////////////绘图///////////////////////////////////////////////////////
    tra = SignalPlanPlot()  # 实例化
    tra.period = 3600  # 数据周期
    tra.gw_speed = 50  # 绿波速度
    tra.arterial_length = 3018.30
    tra.phase_inbound, tra.phase_outbound = phase[0], phase[1]  # 相序
    tra.controllers_num, tra.cycle, tra.offset = 4, cycle, offset  # 交叉口个数，周期，相位差
    tra.inter_location_inbound, tra.inter_location_outbound = (inter_location_inbound,
                                                               inter_location_outbound)
    tra.ari_signal_plan_ring1 = ari_signal_plan_ring[0]  # ring1配时方案
    tra.ari_signal_plan_ring2 = ari_signal_plan_ring[1]  # ring2配时方案
    Load = AterialDataCollection()  # 设置配色、填充样式为默认
    tra.ari_signal_plan_ring1_color = Load.set_signal_color(phase_in, controllers_num=4)
    tra.ari_signal_plan_ring2_color = Load.set_signal_color(phase_out, controllers_num=4)
    tra.ari_signal_plan_ring1_hatch = Load.set_left_signal_hatch(phase_in, controllers_num=4)
    tra.ari_signal_plan_ring2_hatch = Load.set_left_signal_hatch(phase_out, controllers_num=4)
    tra.plot_signal_plan(band_text=(True, 1800))  # 绘制配时方案图，标记带宽
    tra.plot_trajectories(intbound_tradata, outbound_tradata)  # 绘制轨迹
    tra.set_title(title=f'Scenario', fontsize=25)  # 设置标题
    transplt.savefig(f'D:\\CSPT\\Scenario.png', format='png')  # 以PNG文件保存
    transplt.show()  # 显示
    # transplt.close('all')  # 关闭所有图框
    #  ///////////////////////绘制普渡图////////////////////////////////////////////////////
    pu = PurduePlot(cycle=cycle, offset=offset, arterial_length=3018.30)  # 实例化
    pu.inter_location_inbound = inter_location_inbound
    pu.inter_location_outbound = inter_location_outbound
    pu.inbound_tradata = intbound_tradata
    pu.outbound_tradata = outbound_tradata
    pu.ari_signal_plan_ring1 = ari_signal_plan_ring[0]
    pu.ari_signal_plan_ring2 = ari_signal_plan_ring[1]
    pu.phase_inbound = phase[0]
    pu.phase_outbound = phase[1]
    # 绘制普渡图
    pu.plot_purdue()
    #  保存车辆到达数据
    # 存储普渡数据
    pu.save_purdue_data('D:\\CSPT\\PurdueData')  # 存储purdue_data、purdue_BOG_EOG
    # /////////////////////////////////////////////////////////////////////////////////

    # /////////////////////////////评价///////////////////////////////////////////////
    ratedata = (inbound_rate_data, outbound_rate_data)
    inter_location = (inter_location_inbound, inter_location_outbound)
    lane_arterial, lane_side = ([3, 6, 8, 6], [3, 7, 7, 6]), [6, 10, 10, 3]  # 车道数据
    inter_traffic_volume = ([1311, 866, 1430, 1806], [1480, 1788, 1012, 1790])  # 流量数据
    ari_traffic_volume = (1311, 1790)  # 干线流量
    per = RateCoordinationPerformance(ratedata, inter_location, inter_traffic_volume,
                                      ari_traffic_volume, lane_arterial, lane_side)  # 实例化
    per.cycle = cycle
    per.ari_signal_plan_ring1 = ari_signal_plan_ring[0]
    per.ari_signal_plan_ring2 = ari_signal_plan_ring[1]
    per.output_performance_grade()  # 输出评级
    # //////////////////////////////////////////////////////////////////////////////////

    # /////////////////////////////输出数据///////////////////////////////////////////////
    (purdue_data1, purdue_data2) = load_variavle(f'D:\\CSPT\\PurdueData\\purdue_data.pkl')
    (purdue_BOG_EOG1, purdue_BOG_EOG2) = load_variavle(f'D:\\CSPT\\PurdueData\\purdue_BOG_EOG.pkl')
    # 输出绿灯到达率和停车率
    pog1 = output_POG(purdue_data1, purdue_BOG_EOG1)
    pog2 = output_POG(purdue_data2, purdue_BOG_EOG2)
    print('average POG: ', (pog1 + pog2) / 2)
    stop_r1 = output_stop_percent(inter_location_inbound, intbound_tradata, 0)
    stop_r2 = output_stop_percent(inter_location_outbound, outbound_tradata, 0)
    print('average stop percent: ', (stop_r1 + stop_r2) / 2)
    # 输出平均速度
    output_average_speed(inbound_rate_data, f'inbound_avespeed', 'D:\\CSPT\\OUTPUT_Data')
    output_average_speed(outbound_rate_data, f'outbound_avespeed', 'D:\\CSPT\\OUTPUT_Data')
    # 输出延误
    output_stop_delay(inbound_rate_data, 4, f'inbound_delay', 'D:\\CSPT\\OUTPUT_Data')
    output_stop_delay(outbound_rate_data, 4, f'outbound_delay', 'D:\\CSPT\\OUTPUT_Data')


# 场景
# 这里的相位差与文中的相位差不一致的原因是 VIS-SIM4.3 必须在左转相位前调整相位差、
# 即叠加左转相位时间。
if __name__ == "__main__":
    offset, phase_in, phase_out = [0, 96, 15, 61], ['lead', 'lag', 'lag', 'lead'], ['lag', 'lag', 'lag', 'lag']

    ari_signal_plan_ring1 = {"S1": [3.0, 29.0, 2.0, 39.0, 75.0],
                             "S2": [2.0, 43.0, 2.0, 37.0, 64.0],
                             "S3": [2.0, 43.0, 2.0, 38.0, 63.0],
                             "S4": [2.0, 52.0, 2.0, 50.0, 42.0]}

    ari_signal_plan_ring2 = {"S1": [3.0, 43.0, 2.0, 25.0, 75.0],
                             "S2": [2.0, 39.0, 2.0, 41.0, 64.0],
                             "S3": [2.0, 25.0, 2.0, 56.0, 63.0],
                             "S4": [2.0, 39.0, 2.0, 63.0, 42.0]}
    cycle = [148, 148, 148, 148]

    phase = (phase_in, phase_out)
    ari_signal_plan_ring = (ari_signal_plan_ring1, ari_signal_plan_ring2)
    exp()
