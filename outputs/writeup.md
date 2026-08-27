# Báo Cáo Phân Tích & Tối Ưu Hóa Chi Phí GPU (FinOps Write-up)

**Học viên:** Nguyễn Công Việt Quang  
**Mã học viên / MSSV:** 2A202601586  
**Khóa học:** Track 2 (Infrastructure) · Day 25  
**Doanh nghiệp giả định:** NimbusAI  
**Vị trí:** FinOps Lead Engineer  
**Kỳ đánh giá:** Tháng 6/2026  

---

## 1. Tổng Quan Hiệu Quả: Baseline vs. Optimized

| Chỉ số | Trước tối ưu (Baseline) | Sau tối ưu (Optimized) | Mức độ cải thiện / Tiết kiệm |
|---|---|---|---|
| **Tổng chi phí GPU / tháng** | **$27,133** | **$14,626** | **Tiết kiệm $12,507 (46.1%)** |
| **Đơn giá suy luận (`$/1M-token`)** | **$6.488** | **$1.126** | **Giảm 82.6% chi phí đơn vị** |
| **Chi phí Inference / ngày** | $48.87 | $8.48 | Giảm 82.6% |
| **Chi phí Workload / tháng** | $25,667 | $15,627 | Tiết kiệm $10,040 (39.1%) |
| **Lãng phí GPU Idle / tháng** | $600 | $0 (Thu hồi/Tắt) | Loại bỏ 100% lãng phí |
| **Tag Coverage** | 92% | 92% | Đạt chuẩn Chargeback ($\ge 80\%$) |

---

## 2. Phân Tích Các Đòn Bẩy Tiết Kiệm (Savings Levers)

```
[Tổng tiết kiệm: $12,507/tháng]
 ├── Purchasing Strategy (Spot + Reserved 3yr) : $10,040 (80.3%)  ████████████████
 ├── Inference Optimization (Cascade/Cache/Batch): $1,212 (9.7%)   ██
 ├── Right-sizing GPU-Util Lies                 : $655   (5.2%)   █
 └── Kill Idle GPUs                             : $600   (4.8%)   █
```

### 2.1. Đòn bẩy Mua sắm (Purchasing Strategy — Đóng góp lớn nhất: 80.3%)
- **Cơ chế:** Không chạy 100% On-Demand. Dựa trên điểm hòa vốn **55% duty cycle** (tương đương ~13.2h/ngày):
  - Các job chạy liên tục 24/7 (`job-infer-chat`, `job-infer-rag`, `job-infer-search`) chuyển sang **Reserved Instance 3-Year** (chiết khấu ~45%).
  - Các job có thể gián đoạn (`interruptible=1`) như `job-train-llm`, `job-train-embed`, `job-finetune` chuyển sang **Spot Instance kết hợp Checkpointing** (chiết khấu 40–60%).

### 2.2. Đòn bẩy Tối ưu hóa Suy luận (Inference Levers — Giảm 82.6% `$/1M-token`)
- **Model Cascade:** Định tuyến các prompt đơn giản sang model nhỏ ($0.20/$0.40 per 1M) thay vì luôn dùng model lớn ($3.00/$15.00 per 1M).
- **Prompt Caching:** Tận dụng chiết khấu 90% cho các system prompt / context dài được đọc lại nhiều lần.
- **Batch API:** Gom nhóm các tác vụ không cần real-time (ví dụ: eval, batch embedding) để hưởng chiết khấu 50%.
- **Discount Stacking:** Khi kết hợp Batch + Cache hit 100%, chi phí chỉ còn **0.05× (giảm 95%)** so với request thông thường.

---

## 3. Bản Chất Của Hiện Tượng "GPU-Util Lie"

- **Phát hiện:** Hai GPU `gpu-h100-4` (Util 98.2%, MFU 0.194) và `gpu-a10g-1` (Util 96.9%, MFU 0.268) hiển thị mức sử dụng gần 100% trên `nvidia-smi` nhưng hiệu quả tính toán thực tế (MFU) dưới 30%.
- **Nguyên nhân kỹ thuật:** Lệnh `nvidia-smi` chỉ đo tỷ lệ thời gian mà nhân xử lý (GPU clock) có ít nhất 1 kernel đang hoạt động. Trong các tác vụ suy luận Memory-bound (như decode phase của LLM), GPU liên tục bị nghẽn băng thông bộ nhớ (Memory Bandwidth Stall) hoặc chờ I/O. GPU "bận rộn" chờ nạp dữ liệu từ HBM vào SRAM chứ không thực sự tính toán ma trận.
- **Hệ quả tài chính:** NimbusAI đang trả trọn vẹn $2.50/giờ cho H100 nhưng chỉ nhận được 1/5 hiệu năng FLOPS danh định.

---

## 4. Kết Quả Đo Lường 5 Phần Mở Rộng ("Your Turn" Extensions)

### Extension 1: Chính Sách Mua Sắm Nâng Cao (Advanced Tier Policy)
- **Cải tiến:** Tích hợp tỷ lệ gián đoạn thực tế theo dòng GPU (`H100`: 3%, `A100`: 5%, `A10G`: 8%) và phân bổ chính xác giữa Reserved 1-năm vs 3-năm.
- **Kết quả:** Tránh rủi ro cam kết 3 năm cho các job có chu kỳ ngắn, tối ưu chi phí thực tế ở mức **$15,875/tháng (tiết kiệm 38.1%)** với mức độ an toàn SLA cao hơn.

### Extension 2: Right-Sizing Workload Memory-Bound theo MBU & `$/GB-VRAM`
- **Phân tích Catalog:** Đo lường đơn giá băng thông `$/(TB/s BW)`:
  - `MI300X`: $0.368 / (TB/s) & $0.0102 / GB-VRAM (Hiệu quả bộ nhớ cao nhất).
  - `H100`: $0.746 / (TB/s) & $0.0312 / GB-VRAM.
- **Khuyến nghị:** Chuyển đổi `gpu-h100-4` sang `MI300X` (192GB VRAM, 5.3 TB/s BW) giúp tiết kiệm thêm **$396/tháng (22%)** cho riêng GPU này mà vẫn đảm bảo thông lượng bộ nhớ.

### Extension 3: Kinh Tế Học Của Prompt Cache (`cache_is_worth_it`)
- **Điểm hòa vốn:** Với giá ghi cache $3.75/1M và giá đọc giảm 90% ($0.30/1M), điểm hòa vốn là **1.39 lần đọc lại**.
- **Thực tế:** Tỷ lệ Cache Hit Rate toàn hệ thống đạt **31.9%**. Các team `assistant` (Hit 50.8%) và `rag` (Hit 50.9%) đem lại lợi nhuận ròng lần lượt là **$1.72/ngày** và **$1.28/ngày** sau khi đã trừ chi phí ghi cache.

### Extension 4: Quản Trị Ngân Sách & Năng Lượng Cho Traffic Reasoning
- **Phát hiện:** Traffic suy luận có reasoning (`is_reasoning=1`) chỉ chiếm **16.5% số token** nhưng ngốn tới **94.0% tổng năng lượng tiêu thụ suy luận** (29.8 kWh/ngày).
- **Chính sách:** Đề xuất bộ định tuyến có điều kiện (Gated Routing): Chỉ kích hoạt Reasoning khi Confidence Score < 0.85. Giảm 50% traffic reasoning không cần thiết giúp tiết kiệm **14.7 kWh/ngày** (~5.6 kgCO2e/ngày tại us-east-1).

### Extension 5: Lập Lịch Nhận Thức Carbon (Carbon-Aware Scheduling)
- **Thực thi:** Dịch chuyển 5 job training/batch có thể gián đoạn (`interruptible=1`) từ `us-east-1` (380 gCO2/kWh) sang vùng năng lượng thủy điện `europe-north1` (30 gCO2/kWh).
- **Kết quả:** Giảm phát thải carbon từ **679.82 kgCO2e xuống 53.67 kgCO2e** (**cắt giảm 92.1% lượng khí thải** tương đương tránh thải 626.15 kgCO2e/kỳ), đồng thời giảm tiền điện từ $214.68 xuống $161.01.

---

## 5. Top 3 Khuyến Nghị Hành Động Cho NimbusAI

1. **Thực thi Chargeback và Gắn Tag Bắt Buộc (Tag Coverage $\ge 95\%$):**  
   Áp dụng chuẩn FinOps FOCUS và gửi hóa đơn chi phí trực tiếp về 4 team (`assistant`, `search`, `eval`, `rag`). Khi các team phải chịu trách nhiệm tài chính trực tiếp trên ngân sách của mình, hành vi sử dụng tài nguyên sẽ được tự điều chỉnh tối ưu.
2. **Triển khai Spot Instance + Auto-Checkpointing cho toàn bộ Training/Batch:**  
   Chuyển ngay `job-train-llm` và `job-train-embed` sang Spot Instance. Với tỷ lệ ngắt quãng thực tế của H100 chỉ ~3%/giờ và cơ chế checkpoint tự động, công ty sẽ tiết kiệm ngay lập tức **~$5,000/tháng** mà không ảnh hưởng đến tiến độ dự án.
3. **Chuẩn hóa Kiến trúc Inference (Cascade Router + Cache + Gated Reasoning):**  
   Tích hợp LiteLLM Proxy / Gateway có sẵn logic: Tự động cache system prompt, phân luồng cascade prompt ngắn về model nhỏ, gom batch các request bất đồng bộ và kiểm soát chặt chẽ cờ reasoning. Điều này đảm bảo đơn giá phục vụ luôn được chốt ở mức $\approx \$1.126\text{ / 1M-token}$.
