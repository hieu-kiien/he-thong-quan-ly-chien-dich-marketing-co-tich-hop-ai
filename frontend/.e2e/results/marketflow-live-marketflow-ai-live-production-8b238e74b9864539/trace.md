# ✗ MarketFlow AI Live Production E2E Suite (marketing.kienhieu.id.vn) › Full visual E2E tour: Halloween 60fps Auth -&gt; 5-Stage Dashboard -&gt; 4-Agent Squad & Visual Studio -&gt; Custom AI Model Inp…

`e2e-tests/marketflow-live.e2e.ts` · failed · 37.7s

Ran on: browser `chromium 153.0.8010.12` · user agent `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36`

**LOCATOR_NOT_FOUND**

```text
locator matched no nodes within locator("#submit-btn")
```

Waited: 30.0s  
Look at: `e2e-tests/marketflow-live.e2e.ts:5`  

## Steps

1. ✓ `app.open` `/login` (1.2s, video 0:00)
   - screen: 2 nodes at `https://marketing.kienhieu.id.vn/login`
2. ✓ `expect.toBeVisible` `getByRole("button", name: "Đăng nhập").first()` (575ms, video 0:01)
   - expect passed after 3 reads in 575ms: no node (0 matches) x2 -&gt; at 575ms default states (1 match)
3. ✓ `locator.tap` `getByRole("tab", name: "Đăng ký")` (597ms, video 0:01)
   - tap tab "Đăng ký tài khoản" (596ms)
   - screen: 25 changes since step 1 at `https://marketing.kienhieu.id.vn/login`, 25 nodes
     - `added main "Đăng ký tài khoản"`
     - `added region "Tạo không gian mới"`
     - `added button "Bật đêm Halloween"`
     - `added heading "Tạo không gian mới"`
     - `added text="Khởi tạo tài khoản Chuyên viên kèm Không gian làm việc và Tờ giấy Quy tắc Thương hiệu ngay sau 1 bước."`
     - `added tablist "Chế độ xác thực"`
     - `added tab "Đăng nhập"`
     - `added tab "Đăng ký tài khoản" [selected]`
     - `added heading "Đăng ký tài khoản"`
     - `added text="Email"`
     - `added textbox "Email" purpose=username`
     - `added text="Mật khẩu"`
     - 13 more
4. ✓ `locator.pressSequentially` `locator("#register-fullname")` (3.4s, video 0:02)
   - focus textbox "Họ và tên" (69ms)
   - screen: 1 change since step 3 at `https://marketing.kienhieu.id.vn/login`, 25 nodes
     - `changed textbox "Họ và tên" value="Trần Thịnh Hiếu - Kiểm thử E2E Live" (was: textbox "Họ và tên")`
5. ✓ `locator.tap` `getByRole("tab", name: "Đăng nhập")` (117ms, video 0:05)
   - tap tab "Đăng nhập" (117ms)
   - screen: 26 changes since step 4 at `https://marketing.kienhieu.id.vn/login`, 25 nodes
     - `changed main "Đăng nhập" (was: main "Đăng ký tài khoản")`
     - `changed region "Không gian của bạn" (was: region "Tạo không gian mới")`
     - `added heading "Không gian của bạn"`
     - `added text="Đăng nhập để điều phối chiến dịch, kiểm duyệt nội dung và theo dõi số liệu thực đo tại một nơi."`
     - `changed tab "Đăng nhập" [selected] (was: tab "Đăng nhập")`
     - `changed tab "Đăng ký tài khoản" (was: tab "Đăng ký tài khoản" [selected])`
     - `added heading "Đăng nhập"`
     - `added text="Truy cập theo Phân quyền RBAC 3 Vai trò"`
     - `added text="Hỗ trợ đầy đủ Quản lý (Manager), Chuyên viên (Marketer) và Khách hàng duyệt bài (Approver)."`
     - `added text="Điền nhanh tài khoản mẫu (1-Click Demo):"`
     - `added button "Quản lý"`
     - `added button "Marketer"`
     - 14 more
6. ✓ `locator.clear` `locator("#email")` (63ms, video 0:05)
   - clear textbox "Email" (63ms)
   - screen: unchanged since step 5 at `https://marketing.kienhieu.id.vn/login`
7. ✓ `locator.pressSequentially` `locator("#email")` (1.6s, video 0:05)
   - focus textbox "Email" (60ms)
   - screen: 1 change since step 6 at `https://marketing.kienhieu.id.vn/login`, 25 nodes
     - `changed textbox "Email" value="manager@gmail.com" purpose=username (was: textbox "Email" purpose=username)`
8. ✓ `locator.tap` `locator("#password")` (90ms, video 0:07)
   - tap textbox "Mật khẩu" (89ms)
   - screen: unchanged since step 7 at `https://marketing.kienhieu.id.vn/login`
9. ✓ `locator.fill` `locator("#password")` (72ms, video 0:07)
   - fill textbox "Mật khẩu" (72ms)
   - screen: unchanged since step 8 at `https://marketing.kienhieu.id.vn/login`
10. ✗ `locator.tap` `locator("#submit-btn")` (30.0s, video 0:07) — **LOCATOR_NOT_FOUND**

## Screen at failure

`https://marketing.kienhieu.id.vn/login` · viewport 929x925 · 25 nodes  

The screen as the agent reads it, one node per line: `#id role "name" text="…" [states]`.

```text
#root document "Hệ thống Quản lý Chiến dịch Marketing tích hợp AI | AIA331"
 #n3003 main "Đăng nhập"
  #n3004 region "Không gian của bạn"
   #n3005 button "Bật đêm Halloween"
   #n114005 heading "Không gian của bạn"
   #n114006 text="Đăng nhập để điều phối chiến dịch, kiểm duyệt nội dung và theo dõi số liệu thực đo tại một nơi."
  #n3008 tablist "Chế độ xác thực"
   #n3009 tab "Đăng nhập" [selected]
   #n3010 tab "Đăng ký tài khoản"
  #n114007 heading "Đăng nhập"
  #n3012 text="Email"
  #n3013 textbox "Email" value="manager@gmail.com" purpose=username
  #n3014 text="Mật khẩu"
  #n3015 textbox "Mật khẩu" value=<secure> purpose=password [focused secure]
  #n3016 button "Hiện mật khẩu"
  #n114008 text="Truy cập theo Phân quyền RBAC 3 Vai trò"
  #n114009 text="Hỗ trợ đầy đủ Quản lý (Manager), Chuyên viên (Marketer) và Khách hàng duyệt bài (Approver)."
  #n114010 text="Điền nhanh tài khoản mẫu (1-Click Demo):"
  #n114011 button "Quản lý"
  #n114012 button "Marketer"
  #n114013 button "Duyệt bài"
  #n3023 button "Đăng nhập"
   #n3024 text="Đăng nhập"
  #n3025 text="Chưa có tài khoản?"
  #n3026 button "Đăng ký"
```

## Evidence

- [screen](../marketflow-live-marketflow-ai-live-production-04c25be0b41c0c56/attempt-1/screen-at-failure.txt) `.e2e/results/marketflow-live-marketflow-ai-live-production-04c25be0b41c0c56/attempt-1/screen-at-failure.txt`
- [video](../marketflow-live-marketflow-ai-live-production-04c25be0b41c0c56/attempt-1/video/video.webm) `.e2e/results/marketflow-live-marketflow-ai-live-production-04c25be0b41c0c56/attempt-1/video/video.webm`

<sub>e2e 0.20.0 · run `01a13b75-637c-72ab-b2ff-be356d97181c` · the whole run is in `report.json`</sub>
