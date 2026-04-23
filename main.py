import os
import webbrowser
import requests
import folium
from folium import plugins
from geopy.distance import geodesic

# Cấu hình API Key (HÃY THAY KEY CỦA BẠN VÀO ĐÂY)
WEATHER_API_KEY = "1e50238f349acd228e7310187bc68741"

def get_coordinates(city_name):
    # Bước 1 – Lấy tọa độ bằng OpenStreetMap (Nominatim)
    url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
    headers = {"User-Agent": "MyCTAssignmentApp/1.0"}
    response = requests.get(url, headers=headers).json()
    
    if response:
        return float(response[0]['lat']), float(response[0]['lon'])
    return None, None

def get_weather(lat, lon):
    # Bước 2 – Lấy thời tiết bằng OpenWeather API
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric"
    response = requests.get(url).json()
    
    if "main" in response:
        temp = response["main"]["temp"]
        condition = response["weather"][0]["main"]
        desc = response["weather"][0]["description"].capitalize()
        icon_code = response["weather"][0]["icon"]
        return temp, condition, desc, icon_code
    return None, None, None, None

def get_nearby_parks(lat, lon, radius=3000): 
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    overpass_query = f"""
    [out:json];
    (
      node["leisure"="park"](around:{radius},{lat},{lon});
      way["leisure"="park"](around:{radius},{lat},{lon});
      relation["leisure"="park"](around:{radius},{lat},{lon});
      node["leisure"="garden"](around:{radius},{lat},{lon});
      way["leisure"="garden"](around:{radius},{lat},{lon});
      relation["leisure"="garden"](around:{radius},{lat},{lon});
    );
    out center;
    """
    try:
        headers = {"User-Agent": "MyCTAssignmentApp/1.0"}
        response = requests.get(overpass_url, params={'data': overpass_query}, headers=headers)
        
        if response.status_code != 200:
            print(f"  [!] Server Overpass đang bận (Mã lỗi: {response.status_code}).")
            return []
            
        data = response.json()
        parks = []
        from geopy.distance import geodesic
        
        for element in data.get('elements', []):
            tags = element.get('tags', {})
            
            # --- ĐOẠN MỚI THÊM VÀO ---
            # Kiểm tra: Nếu địa điểm không có thẻ 'name' thì bỏ qua, không đưa vào danh sách
            if 'name' not in tags:
                continue 
            # -------------------------

            name = tags['name']
            p_lat = element.get('lat', element.get('center', {}).get('lat'))
            p_lon = element.get('lon', element.get('center', {}).get('lon'))
            
            if p_lat and p_lon:
                distance = geodesic((lat, lon), (p_lat, p_lon)).meters
                parks.append({"name": name, "lat": p_lat, "lon": p_lon, "distance": round(distance, 2)})
                
        # Sắp xếp từ gần đến xa
        return sorted(parks, key=lambda x: x['distance'])
        
    except Exception as e:
        print(f"  [!] Lỗi kết nối Overpass: {e}")
        return []

def get_weather_emoji(icon_code):
    # Ánh xạ mã icon của OpenWeather thành Emoji đẹp mắt
    mapping = {
        '01d': '☀️', '01n': '🌙',       # Trời quang
        '02d': '⛅', '02n': '☁️',       # Ít mây
        '03d': '☁️', '03n': '☁️',       # Mây rải rác
        '04d': '☁️', '04n': '☁️',       # Nhiều mây
        '09d': '🌧️', '09n': '🌧️',       # Mưa rào
        '10d': '🌦️', '10n': '🌧️',       # Mưa
        '11d': '⛈️', '11n': '⛈️',       # Sấm sét
        '13d': '❄️', '13n': '❄️',       # Tuyết
        '50d': '🌫️', '50n': '🌫️'        # Sương mù
    }
    return mapping.get(icon_code, '🌡️') # Mặc định nếu không khớp

def draw_map(city_name, lat, lon, temp, desc, icon_code, parks, radius=3000):
    # 1. Khởi tạo bản đồ, bật thanh tỉ lệ xích (control_scale)
    m = folium.Map(location=[lat, lon], zoom_start=14, control_scale=True)
    
    # 2. Thêm các tùy chọn giao diện bản đồ nền để người xem tự chọn
    folium.TileLayer('OpenStreetMap', name='Bản đồ chuẩn').add_to(m)
    folium.TileLayer('CartoDB positron', name='Bản đồ sáng (CartoDB)').add_to(m)
    folium.TileLayer('CartoDB dark_matter', name='Bản đồ tối (CartoDB)').add_to(m)
    
    # 3. VẼ VÒNG TRÒN BÁN KÍNH TÌM KIẾM (thể hiện rõ tư duy tính toán giới hạn không gian)
    folium.Circle(
        location=[lat, lon],
        radius=radius, # Bán kính bằng số mét bạn tìm kiếm
        color='#3388ff',
        weight=1,
        fill=True,
        fill_color='#3388ff',
        fill_opacity=0.1, # Độ mờ 10%
        tooltip=f"Vùng tìm kiếm: Bán kính {radius/1000} km"
    ).add_to(m)

    # 4. Tạo giao diện đánh dấu trung tâm hiển thị trực tiếp EMOJI + NHIỆT ĐỘ
    emoji = get_weather_emoji(icon_code)
    html_content = f"""
    <div style="
        font-family: Arial, sans-serif; font-size: 14px; color: #333; font-weight: bold; 
        background-color: white; border: 2px solid #ff7800; border-radius: 20px; 
        padding: 5px 10px; white-space: nowrap; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
        text-align: center; display: inline-block;
        ">
        <span style="font-size: 18px;">{emoji}</span> {temp}°C
    </div>
    """
    
    # Popup trung tâm chi tiết hơn
    center_popup = f"<div style='min-width: 150px'><b>{city_name}</b><br>Thời tiết: {desc}<br>Tọa độ: {lat:.4f}, {lon:.4f}</div>"
    
    folium.Marker(
        [lat, lon],
        popup=folium.Popup(center_popup, max_width=300),
        icon=folium.DivIcon(html=html_content, icon_anchor=(30, 20)),
        tooltip="Vị trí Trung tâm"
    ).add_to(m)
    
    # 5. Vẽ marker công viên và đường nối
    for park in parks:
        # Làm đẹp khung Popup thông tin công viên
        park_popup = f"""
        <div style='min-width: 180px'>
            <h4 style='margin-top:0; margin-bottom:5px; color: #2E86C1;'>{park['name']}</h4>
            <b>Cách trung tâm:</b> {park['distance']} m<br>
            <b>Tọa độ:</b> {park['lat']:.4f}, {park['lon']:.4f}
        </div>
        """
        
        folium.Marker(
            [park['lat'], park['lon']],
            popup=folium.Popup(park_popup, max_width=300),
            icon=folium.Icon(color='green', icon='tree', prefix='fa'),
            tooltip=park['name']
        ).add_to(m)
        
        # Đổi đường nối sang màu cam rực rỡ, dễ nhìn hơn trên nền bản đồ
        folium.PolyLine(
            locations=[[lat, lon], [park['lat'], park['lon']]],
            color="#FF5733", 
            weight=2,
            opacity=0.8,
            dash_array='5, 5',
            tooltip=f"{park['distance']} m"
        ).add_to(m)

    # 6. THÊM CÁC CÔNG CỤ TƯƠNG TÁC (PLUGINS)
    # Nút phóng to toàn màn hình
    plugins.Fullscreen(position='topright', title='Phóng to toàn màn hình', title_cancel='Thu nhỏ').add_to(m)
    
    # Thước đo khoảng cách thủ công (rất ấn tượng cho đồ án)
    plugins.MeasureControl(position='topleft', primary_length_unit='meters', primary_area_unit='sqmeters', active_color='#FF5733').add_to(m)
    
    # Bản đồ thu nhỏ ở góc
    plugins.MiniMap(toggle_display=True, position='bottomright').add_to(m)
    
    # Thêm menu chọn Lớp bản đồ
    folium.LayerControl().add_to(m)
        
    m.save("city_weather_parks_map.html")
    print("\n[+] Đã tạo bản đồ")

    file_path = os.path.abspath("city_weather_parks_map.html")
    print("  -> Đang tự động mở bản đồ trên trình duyệt...")
    
    # Yêu cầu hệ điều hành mở file bằng trình duyệt mặc định
    webbrowser.open(f"file:///{file_path}")

def main():
    city = input("Nhập tên một thành phố (Ví dụ: Hồ Chí Minh/Ho Chi Minh): ")
    
    lat, lon = get_coordinates(city)
    if not lat:
        print("Không tìm thấy tọa độ thành phố.")
        return
        
    temp, condition, desc, icon_code = get_weather(lat, lon)
    if not temp:
        print("Lỗi khi lấy dữ liệu thời tiết (Kiểm tra lại API Key).")
        return
        
    parks = get_nearby_parks(lat, lon)
    
    # Bước 4 – Hiển thị kết quả lên màn hình console
    print("-" * 30)
    print(f"City: {city}")
    print(f"Coordinates: ({lat}, {lon})")
    print(f"Weather:")
    print(f"  - Temperature: {temp}°C")
    print(f"  - Condition: {desc}")
    print(f"Nearby places:")
    if parks:
        for i, park in enumerate(parks[:10], 1): # Chỉ in 10 công viên đầu tiên cho gọn
            print(f"  {i}. {park['name']} ({park['distance']} m)")
    else:
        print("  Không tìm thấy công viên nào!")
    
    # Vẽ map
    draw_map(city, lat, lon, temp, desc, icon_code, parks, radius=3000)

if __name__ == "__main__":
    main()