import { useNavigate } from 'react-router-dom';
import { PageContainer } from '@/app/layout/PageContainer';
import { PageHeader, useToast, Card, CardBody } from '@/components/ui';
import { campaignsApi } from '@/lib/api/endpoints';
import { useDocumentTitle } from '@/lib/hooks';
import type { CampaignInput } from '@/lib/types';
import { CampaignForm } from './CampaignForm';

export default function CampaignCreatePage() {
  useDocumentTitle('Tạo chiến dịch');
  const navigate = useNavigate();
  const toast = useToast();

  const handleSubmit = async (body: CampaignInput) => {
    const res = await campaignsApi.create(body);
    toast.success('Tạo chiến dịch thành công', `Chiến dịch "${res.name}" đã được tạo.`);
    navigate(`/campaigns/${res.id}`);
  };

  return (
    <PageContainer>
      <PageHeader
        title="Tạo chiến dịch mới"
        description="Điền thông tin mục tiêu, đối tượng, thời gian, ngân sách và phân bổ kênh cho chiến dịch."
        back={{ to: '/campaigns', label: 'Chiến dịch' }}
      />
      <div className="mx-auto max-w-3xl">
        <Card>
          <CardBody>
            <CampaignForm
              submitLabel="Tạo chiến dịch"
              onSubmit={handleSubmit}
              onCancel={() => navigate('/campaigns')}
            />
          </CardBody>
        </Card>
      </div>
    </PageContainer>
  );
}
