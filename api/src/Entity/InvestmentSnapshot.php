<?php
namespace App\Entity;

use Doctrine\ORM\Mapping as ORM;

#[ORM\Entity]
#[ORM\Table(name: 'investment_snapshots')]
#[ORM\Index(name: 'idx_snapshot_investment', columns: ['investment_id'])]
class InvestmentSnapshot
{
    #[ORM\Id, ORM\Column(type: 'string', length: 36, options: ['fixed' => true])]
    public string $id;
    #[ORM\ManyToOne(targetEntity: Investment::class), ORM\JoinColumn(name: 'investment_id', nullable: false, onDelete: 'CASCADE')]
    public Investment $investment;
    #[ORM\Column(type: 'date_immutable')]
    public \DateTimeImmutable $date;
    #[ORM\Column(name: 'market_value', type: 'decimal', precision: 15, scale: 2)]
    public string $marketValue;
    #[ORM\Column(type: 'decimal', precision: 15, scale: 2, options: ['default' => '0.00'])]
    public string $contribution;
    #[ORM\Column(type: 'decimal', precision: 15, scale: 2, options: ['default' => '0.00'])]
    public string $withdrawal;
    #[ORM\Column(length: 255, options: ['default' => ''])]
    public string $note;

    public function __construct(string $id, Investment $investment, string $date, string $marketValue, string $contribution, string $withdrawal, string $note)
    {
        $this->id = $id;
        $this->investment = $investment;
        $this->date = new \DateTimeImmutable($date);
        $this->marketValue = $marketValue;
        $this->contribution = $contribution;
        $this->withdrawal = $withdrawal;
        $this->note = $note;
    }
}
